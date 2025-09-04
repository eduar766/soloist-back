"""
Automatic file cleanup service.
Handles cleanup of temporary files, orphaned uploads, and old files.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.infrastructure.storage.storage_service import get_storage_service
from app.infrastructure.storage.bucket_manager import get_bucket_manager
from app.config import settings


logger = logging.getLogger(__name__)


@dataclass
class CleanupRule:
    """Rule for automatic file cleanup."""
    bucket: str
    folder_pattern: str
    max_age_days: int
    max_files_per_user: Optional[int] = None
    file_pattern: Optional[str] = None
    description: str = ""


class CleanupService:
    """Service for automatic file cleanup operations."""
    
    def __init__(self):
        """Initialize cleanup service with default rules."""
        self.cleanup_rules = [
            CleanupRule(
                bucket="temp",
                folder_pattern="*",
                max_age_days=1,
                description="Clean temporary files older than 1 day"
            ),
            CleanupRule(
                bucket="documents",
                folder_pattern="invoices/*/temp_*",
                max_age_days=7,
                description="Clean temporary invoice PDFs older than 7 days"
            ),
            CleanupRule(
                bucket="attachments",
                folder_pattern="temp/*",
                max_age_days=3,
                description="Clean temporary attachment uploads older than 3 days"
            ),
            CleanupRule(
                bucket="logos",
                folder_pattern="temp/*",
                max_age_days=2,
                description="Clean temporary logo uploads older than 2 days"
            ),
            CleanupRule(
                bucket="avatars",
                folder_pattern="*/old_*",
                max_age_days=30,
                max_files_per_user=5,
                description="Clean old avatar versions, keep max 5 per user"
            )
        ]
    
    async def run_cleanup(
        self,
        dry_run: bool = True,
        specific_bucket: Optional[str] = None,
        specific_rule: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run cleanup operations based on rules.
        
        Args:
            dry_run: If True, only report what would be deleted
            specific_bucket: Run cleanup only for specific bucket
            specific_rule: Run only specific cleanup rule
            
        Returns:
            Cleanup results summary
        """
        logger.info(f"Starting cleanup operation (dry_run={dry_run})")
        
        results = {
            "started_at": datetime.now().isoformat(),
            "dry_run": dry_run,
            "rules_processed": 0,
            "total_files_found": 0,
            "total_files_deleted": 0,
            "total_size_freed_mb": 0,
            "errors": [],
            "rule_results": []
        }
        
        bucket_manager = get_bucket_manager()
        
        # Filter rules if specific bucket or rule specified
        rules_to_process = self.cleanup_rules
        if specific_bucket:
            rules_to_process = [r for r in rules_to_process if r.bucket == specific_bucket]
        if specific_rule:
            rules_to_process = [r for r in rules_to_process if specific_rule in r.description]
        
        for rule in rules_to_process:
            try:
                rule_result = await self._process_cleanup_rule(rule, dry_run, bucket_manager)
                results["rule_results"].append(rule_result)
                results["rules_processed"] += 1
                results["total_files_found"] += rule_result["files_found"]
                results["total_files_deleted"] += rule_result["files_deleted"]
                results["total_size_freed_mb"] += rule_result["size_freed_mb"]
                
            except Exception as e:
                error_msg = f"Error processing rule for {rule.bucket}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        results["completed_at"] = datetime.now().isoformat()
        logger.info(f"Cleanup completed. Found {results['total_files_found']} files, "
                   f"deleted {results['total_files_deleted']} files")
        
        return results
    
    async def _process_cleanup_rule(
        self,
        rule: CleanupRule,
        dry_run: bool,
        bucket_manager
    ) -> Dict[str, Any]:
        """Process a single cleanup rule."""
        logger.info(f"Processing cleanup rule: {rule.description}")
        
        result = {
            "rule": rule.description,
            "bucket": rule.bucket,
            "files_found": 0,
            "files_deleted": 0,
            "size_freed_mb": 0,
            "errors": []
        }
        
        try:
            storage_service = get_storage_service()
            
            # Get all files in bucket
            files = await storage_service.list_files(bucket=rule.bucket)
            
            # Filter files based on rule criteria
            files_to_delete = self._filter_files_by_rule(files, rule)
            
            result["files_found"] = len(files_to_delete)
            
            if not dry_run and files_to_delete:
                # Delete files in batches
                deleted_files, total_size = await self._delete_files_batch(
                    files_to_delete, rule.bucket, storage_service
                )
                result["files_deleted"] = deleted_files
                result["size_freed_mb"] = round(total_size / (1024 * 1024), 2)
            
        except Exception as e:
            error_msg = f"Error in cleanup rule processing: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
        
        return result
    
    def _filter_files_by_rule(self, files: List[Dict], rule: CleanupRule) -> List[Dict]:
        """Filter files based on cleanup rule criteria."""
        cutoff_date = datetime.now() - timedelta(days=rule.max_age_days)
        files_to_delete = []
        
        # Group files by user if max_files_per_user is specified
        user_files = {}
        
        for file_info in files:
            try:
                # Check age criteria
                file_date = datetime.fromisoformat(
                    file_info["created_at"].replace("Z", "+00:00")
                )
                
                file_path = file_info["name"]
                
                # Check folder pattern matching (simplified)
                if not self._matches_pattern(file_path, rule.folder_pattern):
                    continue
                
                # Check file pattern if specified
                if rule.file_pattern and not self._matches_pattern(file_path, rule.file_pattern):
                    continue
                
                # Check age
                if file_date < cutoff_date:
                    if rule.max_files_per_user:
                        # Group by user folder
                        user_folder = file_path.split("/")[0] if "/" in file_path else "root"
                        if user_folder not in user_files:
                            user_files[user_folder] = []
                        user_files[user_folder].append((file_info, file_date))
                    else:
                        files_to_delete.append(file_info)
                
            except Exception as e:
                logger.warning(f"Error processing file {file_info.get('name', 'unknown')}: {e}")
                continue
        
        # Handle max_files_per_user constraint
        if rule.max_files_per_user and user_files:
            for user_folder, user_file_list in user_files.items():
                # Sort by date (oldest first) and take excess files
                user_file_list.sort(key=lambda x: x[1])
                if len(user_file_list) > rule.max_files_per_user:
                    excess_files = user_file_list[:-rule.max_files_per_user]
                    files_to_delete.extend([f[0] for f in excess_files])
        
        return files_to_delete
    
    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Simple pattern matching (supports * wildcards)."""
        if pattern == "*":
            return True
        
        # Convert simple glob pattern to basic matching
        if "*" in pattern:
            parts = pattern.split("*")
            path_matches = True
            current_path = file_path
            
            for i, part in enumerate(parts):
                if not part:  # Empty part from consecutive *
                    continue
                
                if i == 0:  # First part - should match start
                    if not current_path.startswith(part):
                        path_matches = False
                        break
                    current_path = current_path[len(part):]
                elif i == len(parts) - 1:  # Last part - should match end
                    if not current_path.endswith(part):
                        path_matches = False
                        break
                else:  # Middle part - should be found
                    if part not in current_path:
                        path_matches = False
                        break
                    current_path = current_path[current_path.find(part) + len(part):]
            
            return path_matches
        else:
            return pattern in file_path
    
    async def _delete_files_batch(
        self,
        files: List[Dict],
        bucket: str,
        storage_service,
        batch_size: int = 50
    ) -> tuple[int, int]:
        """Delete files in batches and return count and total size."""
        deleted_count = 0
        total_size = 0
        
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            
            for file_info in batch:
                try:
                    file_path = file_info["name"]
                    file_size = file_info.get("metadata", {}).get("size", 0)
                    
                    success = await storage_service.delete_file(file_path, bucket)
                    if success:
                        deleted_count += 1
                        total_size += file_size
                    
                except Exception as e:
                    logger.warning(f"Failed to delete file {file_info.get('name')}: {e}")
            
            # Small delay between batches to avoid rate limiting
            await asyncio.sleep(0.1)
        
        return deleted_count, total_size
    
    async def cleanup_orphaned_uploads(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Clean up orphaned uploads (files uploaded but not referenced in database).
        """
        logger.info("Starting orphaned uploads cleanup")
        
        # TODO: This would require cross-referencing storage files with database records
        # For now, return a placeholder result
        
        return {
            "operation": "cleanup_orphaned_uploads",
            "dry_run": dry_run,
            "files_found": 0,
            "files_deleted": 0,
            "message": "Orphaned uploads cleanup not yet implemented - requires database integration"
        }
    
    async def get_cleanup_suggestions(self, user_id: str) -> Dict[str, Any]:
        """
        Get cleanup suggestions for a specific user.
        """
        suggestions = {
            "user_id": user_id,
            "suggestions": [],
            "potential_savings_mb": 0
        }
        
        try:
            bucket_manager = get_bucket_manager()
            
            # Check each bucket for user's files
            for bucket_name in bucket_manager.list_bucket_configs().keys():
                bucket_stats = await bucket_manager.get_bucket_usage(bucket_name)
                user_stats = bucket_stats.get("user_usage", {}).get(user_id, {})
                
                if user_stats.get("files", 0) > 0:
                    # Check for old files
                    storage_service = get_storage_service()
                    files = await storage_service.list_files(bucket=bucket_name)
                    
                    old_files = []
                    cutoff_date = datetime.now() - timedelta(days=30)
                    
                    for file_info in files:
                        if user_id in file_info["name"]:  # User's file
                            try:
                                file_date = datetime.fromisoformat(
                                    file_info["created_at"].replace("Z", "+00:00")
                                )
                                if file_date < cutoff_date:
                                    old_files.append(file_info)
                            except:
                                continue
                    
                    if old_files:
                        total_size = sum(f.get("metadata", {}).get("size", 0) for f in old_files)
                        suggestions["suggestions"].append({
                            "bucket": bucket_name,
                            "type": "old_files",
                            "files_count": len(old_files),
                            "size_mb": round(total_size / (1024 * 1024), 2),
                            "description": f"{len(old_files)} files older than 30 days in {bucket_name}"
                        })
                        suggestions["potential_savings_mb"] += round(total_size / (1024 * 1024), 2)
        
        except Exception as e:
            logger.error(f"Error getting cleanup suggestions: {e}")
        
        return suggestions
    
    def add_cleanup_rule(self, rule: CleanupRule) -> None:
        """Add a custom cleanup rule."""
        self.cleanup_rules.append(rule)
        logger.info(f"Added cleanup rule: {rule.description}")
    
    def list_cleanup_rules(self) -> List[Dict[str, Any]]:
        """List all cleanup rules."""
        return [
            {
                "bucket": rule.bucket,
                "folder_pattern": rule.folder_pattern,
                "max_age_days": rule.max_age_days,
                "max_files_per_user": rule.max_files_per_user,
                "file_pattern": rule.file_pattern,
                "description": rule.description
            }
            for rule in self.cleanup_rules
        ]


# Create singleton instance
_cleanup_service = None

def get_cleanup_service() -> CleanupService:
    """Get singleton cleanup service instance."""
    global _cleanup_service
    if _cleanup_service is None:
        _cleanup_service = CleanupService()
    return _cleanup_service


# Background task function for scheduled cleanup
async def run_scheduled_cleanup():
    """Run scheduled cleanup as background task."""
    cleanup_service = get_cleanup_service()
    
    try:
        # Run cleanup every day at 2 AM (this would be called by a scheduler)
        result = await cleanup_service.run_cleanup(dry_run=False)
        logger.info(f"Scheduled cleanup completed: {result}")
    except Exception as e:
        logger.error(f"Scheduled cleanup failed: {e}")