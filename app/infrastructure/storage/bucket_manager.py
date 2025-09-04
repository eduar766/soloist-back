"""
Supabase Storage bucket management.
Handles bucket creation, policies, and configuration.
"""

from typing import List, Dict, Any, Optional
from supabase import Client
import json


class BucketManager:
    """Manages Supabase Storage buckets and their policies."""
    
    def __init__(self, supabase_client: Client):
        """Initialize bucket manager with Supabase client."""
        self.client = supabase_client
        
        # Bucket configurations
        self.bucket_configs = {
            "documents": {
                "name": "documents",
                "public": False,
                "allowed_mime_types": [
                    "application/pdf",
                    "text/plain",
                    "application/msword",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ],
                "file_size_limit": 20 * 1024 * 1024,  # 20MB
                "description": "Invoice PDFs, reports and general documents"
            },
            "logos": {
                "name": "logos",
                "public": True,
                "allowed_mime_types": [
                    "image/jpeg",
                    "image/png",
                    "image/gif",
                    "image/webp",
                    "image/svg+xml"
                ],
                "file_size_limit": 5 * 1024 * 1024,  # 5MB
                "description": "Company and client logos"
            },
            "attachments": {
                "name": "attachments",
                "public": False,
                "allowed_mime_types": [
                    "image/jpeg",
                    "image/png",
                    "image/gif",
                    "image/webp",
                    "application/pdf",
                    "text/plain",
                    "application/zip",
                    "application/x-zip-compressed"
                ],
                "file_size_limit": 10 * 1024 * 1024,  # 10MB
                "description": "Task and project file attachments"
            },
            "temp": {
                "name": "temp",
                "public": False,
                "allowed_mime_types": ["*/*"],
                "file_size_limit": 50 * 1024 * 1024,  # 50MB
                "description": "Temporary files with auto-cleanup"
            },
            "avatars": {
                "name": "avatars",
                "public": True,
                "allowed_mime_types": [
                    "image/jpeg",
                    "image/png",
                    "image/gif",
                    "image/webp"
                ],
                "file_size_limit": 2 * 1024 * 1024,  # 2MB
                "description": "User profile avatars"
            }
        }
    
    async def initialize_buckets(self) -> Dict[str, Any]:
        """Initialize all required buckets with proper policies."""
        results = {
            "created": [],
            "existing": [],
            "errors": []
        }
        
        for bucket_name, config in self.bucket_configs.items():
            try:
                # Check if bucket exists
                existing_buckets = self.client.storage.list_buckets()
                bucket_exists = any(b["name"] == bucket_name for b in existing_buckets)
                
                if not bucket_exists:
                    # Create bucket
                    result = self.client.storage.create_bucket(
                        bucket_name,
                        options={
                            "public": config["public"],
                            "allowed_mime_types": config["allowed_mime_types"],
                            "file_size_limit": config["file_size_limit"]
                        }
                    )
                    
                    if result.get("name") == bucket_name:
                        results["created"].append(bucket_name)
                        
                        # Set up RLS policies
                        await self._setup_bucket_policies(bucket_name, config)
                    else:
                        results["errors"].append(f"Failed to create {bucket_name}")
                else:
                    results["existing"].append(bucket_name)
                    
            except Exception as e:
                results["errors"].append(f"Error with {bucket_name}: {str(e)}")
        
        return results
    
    async def _setup_bucket_policies(self, bucket_name: str, config: Dict[str, Any]) -> None:
        """Set up Row Level Security policies for a bucket."""
        
        # Policy templates based on bucket type
        if bucket_name == "logos":
            # Public read, authenticated write for own files
            policies = [
                {
                    "name": f"Public read access for {bucket_name}",
                    "definition": "true",
                    "command": "SELECT"
                },
                {
                    "name": f"Authenticated users can upload to {bucket_name}",
                    "definition": "auth.uid()::text = (storage.foldername(name))[1]",
                    "command": "INSERT"
                },
                {
                    "name": f"Users can update own files in {bucket_name}",
                    "definition": "auth.uid()::text = (storage.foldername(name))[1]",
                    "command": "UPDATE"
                },
                {
                    "name": f"Users can delete own files in {bucket_name}",
                    "definition": "auth.uid()::text = (storage.foldername(name))[1]",
                    "command": "DELETE"
                }
            ]
        
        elif bucket_name == "avatars":
            # Public read, users can manage own avatars
            policies = [
                {
                    "name": f"Public read access for {bucket_name}",
                    "definition": "true",
                    "command": "SELECT"
                },
                {
                    "name": f"Users can upload own avatar to {bucket_name}",
                    "definition": "auth.uid()::text = (storage.foldername(name))[1]",
                    "command": "INSERT"
                },
                {
                    "name": f"Users can update own avatar in {bucket_name}",
                    "definition": "auth.uid()::text = (storage.foldername(name))[1]",
                    "command": "UPDATE"
                },
                {
                    "name": f"Users can delete own avatar in {bucket_name}",
                    "definition": "auth.uid()::text = (storage.foldername(name))[1]",
                    "command": "DELETE"
                }
            ]
        
        else:
            # Private buckets - users can only access their own files
            policies = [
                {
                    "name": f"Users can view own files in {bucket_name}",
                    "definition": "auth.uid()::text = (storage.foldername(name))[1]",
                    "command": "SELECT"
                },
                {
                    "name": f"Users can upload to {bucket_name}",
                    "definition": "auth.uid()::text = (storage.foldername(name))[1]",
                    "command": "INSERT"
                },
                {
                    "name": f"Users can update own files in {bucket_name}",
                    "definition": "auth.uid()::text = (storage.foldername(name))[1]",
                    "command": "UPDATE"
                },
                {
                    "name": f"Users can delete own files in {bucket_name}",
                    "definition": "auth.uid()::text = (storage.foldername(name))[1]",
                    "command": "DELETE"
                }
            ]
        
        # Create policies using Supabase admin client
        for policy in policies:
            try:
                # Note: In a real implementation, you'd use the Supabase management API
                # or execute SQL directly to create these policies
                print(f"Would create policy: {policy['name']} for bucket {bucket_name}")
            except Exception as e:
                print(f"Error creating policy {policy['name']}: {str(e)}")
    
    def get_bucket_config(self, bucket_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific bucket."""
        return self.bucket_configs.get(bucket_name)
    
    def list_bucket_configs(self) -> Dict[str, Dict[str, Any]]:
        """List all bucket configurations."""
        return self.bucket_configs.copy()
    
    async def get_bucket_usage(self, bucket_name: str) -> Dict[str, Any]:
        """Get usage statistics for a bucket."""
        try:
            # List all files in bucket
            files = self.client.storage.from_(bucket_name).list()
            
            total_files = len(files)
            total_size = sum(file.get("metadata", {}).get("size", 0) for file in files)
            
            # Group by folder (user)
            user_usage = {}
            for file in files:
                folder = file["name"].split("/")[0] if "/" in file["name"] else "root"
                if folder not in user_usage:
                    user_usage[folder] = {"files": 0, "size": 0}
                user_usage[folder]["files"] += 1
                user_usage[folder]["size"] += file.get("metadata", {}).get("size", 0)
            
            return {
                "bucket": bucket_name,
                "total_files": total_files,
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "user_usage": user_usage
            }
            
        except Exception as e:
            return {
                "bucket": bucket_name,
                "error": str(e)
            }
    
    async def cleanup_bucket(
        self, 
        bucket_name: str, 
        older_than_days: int = 7,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Clean up old files in a bucket."""
        from datetime import datetime, timedelta
        
        try:
            files = self.client.storage.from_(bucket_name).list()
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            
            files_to_delete = []
            for file in files:
                file_date = datetime.fromisoformat(
                    file["created_at"].replace("Z", "+00:00")
                )
                if file_date < cutoff_date:
                    files_to_delete.append(file["name"])
            
            result = {
                "bucket": bucket_name,
                "files_found": len(files_to_delete),
                "dry_run": dry_run,
                "files_to_delete": files_to_delete[:10]  # Show first 10
            }
            
            if not dry_run and files_to_delete:
                # Delete files in batches
                batch_size = 100
                deleted_count = 0
                
                for i in range(0, len(files_to_delete), batch_size):
                    batch = files_to_delete[i:i + batch_size]
                    delete_result = self.client.storage.from_(bucket_name).remove(batch)
                    if delete_result.status_code == 200:
                        deleted_count += len(batch)
                
                result["deleted_count"] = deleted_count
            
            return result
            
        except Exception as e:
            return {
                "bucket": bucket_name,
                "error": str(e)
            }
    
    def validate_file_for_bucket(
        self, 
        bucket_name: str, 
        file_size: int, 
        content_type: str
    ) -> Dict[str, Any]:
        """Validate if a file can be uploaded to a specific bucket."""
        config = self.get_bucket_config(bucket_name)
        if not config:
            return {
                "valid": False,
                "error": f"Unknown bucket: {bucket_name}"
            }
        
        # Check file size
        if file_size > config["file_size_limit"]:
            return {
                "valid": False,
                "error": f"File too large. Max size: {config['file_size_limit'] / 1024 / 1024:.1f}MB"
            }
        
        # Check content type
        allowed_types = config["allowed_mime_types"]
        if "*/*" not in allowed_types and content_type not in allowed_types:
            return {
                "valid": False,
                "error": f"File type not allowed. Allowed types: {', '.join(allowed_types)}"
            }
        
        return {"valid": True}


# Create singleton instance
_bucket_manager = None

def get_bucket_manager() -> BucketManager:
    """Get singleton bucket manager instance."""
    global _bucket_manager
    if _bucket_manager is None:
        from app.infrastructure.auth.supabase_client import get_supabase_client
        _bucket_manager = BucketManager(get_supabase_client())
    return _bucket_manager