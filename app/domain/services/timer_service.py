"""Timer service for managing time tracking logic.
Handles timer operations, validations, and business rules.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.domain.models.base import BusinessRuleViolation, ValidationError, TimeRange
from app.domain.models.time_entry import TimeEntry, TimeEntryStatus, TimeEntryType
from app.domain.models.project import Project
from app.domain.models.task import Task


class TimerService:
    """
    Domain service for time tracking logic and validations.
    Handles timer operations, overlap detection, and business rules.
    """

    def __init__(self):
        self.max_daily_hours = 24.0
        self.max_single_session_hours = 16.0
        self.min_session_minutes = 1
        self.idle_timeout_minutes = 30

    def start_timer(
        self,
        user_id: str,
        project_id: int,
        task_id: Optional[int] = None,
        description: Optional[str] = None,
        hourly_rate: Optional[float] = None,
        stop_other_timers: bool = True
    ) -> TimeEntry:
        """
        Start a new timer for time tracking.
        """
        # Validate inputs
        if not user_id:
            raise ValidationError("User ID is required", "user_id")
        
        if not project_id:
            raise ValidationError("Project ID is required", "project_id")
        
        if hourly_rate is not None and hourly_rate < 0:
            raise ValidationError("Hourly rate cannot be negative", "hourly_rate")
        
        # Create time entry with running status
        time_entry = TimeEntry(
            user_id=user_id,
            project_id=project_id,
            task_id=task_id,
            description=description,
            entry_type=TimeEntryType.TIMER,
            status=TimeEntryStatus.STOPPED,  # Will be changed to running
            hourly_rate=hourly_rate
        )
        
        # Start the timer
        time_entry.start_timer()
        
        return time_entry

    def stop_timer(
        self,
        time_entry: TimeEntry,
        end_time: Optional[datetime] = None
    ) -> TimeEntry:
        """
        Stop a running timer.
        """
        if not time_entry.is_running:
            raise BusinessRuleViolation("Timer is not running")
        
        # Stop the timer
        time_entry.stop_timer(end_time)
        
        # Validate the session
        self._validate_time_session(time_entry)
        
        return time_entry

    def pause_timer(self, time_entry: TimeEntry) -> TimeEntry:
        """
        Pause a running timer (implementation depends on requirements).
        For now, we'll stop it and allow manual restart.
        """
        if not time_entry.is_running:
            raise BusinessRuleViolation("Timer is not running")
        
        # Stop the current session
        time_entry.stop_timer()
        
        # Mark as paused (could add pause status if needed)
        return time_entry

    def resume_timer(
        self,
        time_entry: TimeEntry,
        continue_description: bool = True
    ) -> TimeEntry:
        """
        Resume a paused timer by creating a new timer session.
        """
        if time_entry.is_running:
            raise BusinessRuleViolation("Timer is already running")
        
        # Create a new timer session based on the previous one
        new_entry = TimeEntry(
            user_id=time_entry.user_id,
            project_id=time_entry.project_id,
            task_id=time_entry.task_id,
            description=time_entry.description if continue_description else None,
            entry_type=TimeEntryType.TIMER,
            hourly_rate=time_entry.hourly_rate,
            billable=time_entry.billable
        )
        
        new_entry.start_timer()
        return new_entry

    def create_manual_entry(
        self,
        user_id: str,
        project_id: int,
        duration_minutes: int,
        start_time: Optional[datetime] = None,
        task_id: Optional[int] = None,
        description: Optional[str] = None,
        hourly_rate: Optional[float] = None,
        billable: bool = True,
        date: Optional[datetime] = None
    ) -> TimeEntry:
        """
        Create a manual time entry.
        """
        if duration_minutes < self.min_session_minutes:
            raise ValidationError(
                f"Duration must be at least {self.min_session_minutes} minute(s)",
                "duration_minutes"
            )
        
        if duration_minutes > (self.max_single_session_hours * 60):
            raise ValidationError(
                f"Duration cannot exceed {self.max_single_session_hours} hours",
                "duration_minutes"
            )
        
        entry_date = date.date() if date else datetime.now().date()
        
        time_entry = TimeEntry.create_manual_entry(
            user_id=user_id,
            project_id=project_id,
            duration_minutes=duration_minutes,
            description=description,
            task_id=task_id,
            billable=billable,
            hourly_rate=hourly_rate,
            date=entry_date
        )
        
        # Set time range if start time provided
        if start_time:
            end_time = start_time + timedelta(minutes=duration_minutes)
            time_entry.time_range = TimeRange(start=start_time, end=end_time)
        
        # Validate the entry
        self._validate_time_session(time_entry)
        
        return time_entry

    def update_time_entry(
        self,
        time_entry: TimeEntry,
        duration_minutes: Optional[int] = None,
        description: Optional[str] = None,
        hourly_rate: Optional[float] = None,
        billable: Optional[bool] = None
    ) -> TimeEntry:
        """
        Update an existing time entry.
        """
        if not time_entry.can_be_edited:
            raise BusinessRuleViolation("Time entry cannot be edited")
        
        # Update duration if provided
        if duration_minutes is not None:
            if duration_minutes < self.min_session_minutes:
                raise ValidationError(
                    f"Duration must be at least {self.min_session_minutes} minute(s)",
                    "duration_minutes"
                )
            
            if duration_minutes > (self.max_single_session_hours * 60):
                raise ValidationError(
                    f"Duration cannot exceed {self.max_single_session_hours} hours",
                    "duration_minutes"
                )
            
            time_entry.update_duration(duration_minutes)
        
        # Update other fields
        time_entry.update_info(
            description=description,
            hourly_rate=hourly_rate,
            billable=billable
        )
        
        # Validate after updates
        self._validate_time_session(time_entry)
        
        return time_entry

    def detect_overlapping_entries(
        self,
        time_entries: List[TimeEntry],
        new_entry: TimeEntry
    ) -> List[TimeEntry]:
        """
        Detect time entries that overlap with a new entry.
        """
        if not new_entry.time_range or new_entry.time_range.is_open:
            return []
        
        overlapping = []
        
        for entry in time_entries:
            if entry.id == new_entry.id:
                continue
            
            if not entry.time_range or entry.time_range.is_open:
                continue
            
            if new_entry.time_range.overlaps_with(entry.time_range):
                overlapping.append(entry)
        
        return overlapping

    def validate_daily_hours(
        self,
        user_id: str,
        date: datetime,
        existing_entries: List[TimeEntry],
        new_duration_hours: float
    ) -> bool:
        """
        Validate that daily hours don't exceed maximum.
        """
        # Calculate existing hours for the date
        existing_hours = sum(
            entry.duration_hours for entry in existing_entries
            if entry.user_id == user_id and entry.date == date.date()
        )
        
        total_hours = existing_hours + new_duration_hours
        
        if total_hours > self.max_daily_hours:
            raise BusinessRuleViolation(
                f"Daily hours would exceed maximum of {self.max_daily_hours} hours "
                f"(current: {existing_hours:.2f}h, adding: {new_duration_hours:.2f}h)"
            )
        
        return True

    def calculate_idle_time(
        self,
        start_time: datetime,
        end_time: datetime,
        activity_timestamps: List[datetime]
    ) -> Dict[str, Any]:
        """
        Calculate idle time based on activity timestamps.
        This is a simplified implementation - real system would track mouse/keyboard activity.
        """
        if not activity_timestamps:
            # No activity recorded - consider entire session as potentially idle
            total_minutes = int((end_time - start_time).total_seconds() / 60)
            return {
                "total_session_minutes": total_minutes,
                "idle_minutes": total_minutes,
                "active_minutes": 0,
                "idle_percentage": 100.0,
                "idle_periods": [(start_time, end_time)]
            }
        
        # Sort activity timestamps
        activity_timestamps.sort()
        
        idle_periods = []
        idle_minutes = 0
        
        # Check for idle time at the beginning
        if activity_timestamps[0] - start_time > timedelta(minutes=self.idle_timeout_minutes):
            idle_start = start_time
            idle_end = activity_timestamps[0] - timedelta(minutes=self.idle_timeout_minutes)
            idle_periods.append((idle_start, idle_end))
            idle_minutes += int((idle_end - idle_start).total_seconds() / 60)
        
        # Check for idle time between activities
        for i in range(1, len(activity_timestamps)):
            gap = activity_timestamps[i] - activity_timestamps[i-1]
            if gap > timedelta(minutes=self.idle_timeout_minutes * 2):
                idle_start = activity_timestamps[i-1] + timedelta(minutes=self.idle_timeout_minutes)
                idle_end = activity_timestamps[i] - timedelta(minutes=self.idle_timeout_minutes)
                idle_periods.append((idle_start, idle_end))
                idle_minutes += int((idle_end - idle_start).total_seconds() / 60)
        
        # Check for idle time at the end
        if end_time - activity_timestamps[-1] > timedelta(minutes=self.idle_timeout_minutes):
            idle_start = activity_timestamps[-1] + timedelta(minutes=self.idle_timeout_minutes)
            idle_end = end_time
            idle_periods.append((idle_start, idle_end))
            idle_minutes += int((idle_end - idle_start).total_seconds() / 60)
        
        total_minutes = int((end_time - start_time).total_seconds() / 60)
        active_minutes = max(0, total_minutes - idle_minutes)
        idle_percentage = (idle_minutes / total_minutes * 100) if total_minutes > 0 else 0
        
        return {
            "total_session_minutes": total_minutes,
            "idle_minutes": idle_minutes,
            "active_minutes": active_minutes,
            "idle_percentage": round(idle_percentage, 1),
            "idle_periods": idle_periods,
            "activity_count": len(activity_timestamps)
        }

    def suggest_time_adjustments(
        self,
        time_entry: TimeEntry,
        activity_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Suggest adjustments to time entry based on activity data.
        """
        suggestions = {
            "recommended_adjustments": [],
            "confidence_score": 1.0,
            "original_duration_minutes": time_entry.duration_minutes,
            "suggested_duration_minutes": time_entry.duration_minutes
        }
        
        if not activity_data:
            return suggestions
        
        # Analyze idle time
        if "idle_percentage" in activity_data:
            idle_percentage = activity_data["idle_percentage"]
            
            if idle_percentage > 50:
                # High idle time - suggest reduction
                active_minutes = activity_data.get("active_minutes", time_entry.duration_minutes)
                buffer_minutes = max(5, int(active_minutes * 0.1))  # 10% buffer, minimum 5 minutes
                suggested_minutes = active_minutes + buffer_minutes
                
                suggestions["recommended_adjustments"].append({
                    "type": "duration_reduction",
                    "reason": f"High idle time detected ({idle_percentage:.1f}%)",
                    "suggested_duration_minutes": suggested_minutes,
                    "time_saved_minutes": time_entry.duration_minutes - suggested_minutes
                })
                
                suggestions["suggested_duration_minutes"] = suggested_minutes
                suggestions["confidence_score"] = min(1.0, idle_percentage / 100)
        
        # Check for very short sessions
        if time_entry.duration_minutes < 10:
            suggestions["recommended_adjustments"].append({
                "type": "short_session_warning",
                "reason": "Very short time tracking session",
                "suggestion": "Consider combining with other short sessions or adding more context"
            })
        
        # Check for very long sessions
        if time_entry.duration_hours > 8:
            suggestions["recommended_adjustments"].append({
                "type": "long_session_warning",
                "reason": "Very long time tracking session",
                "suggestion": "Consider breaking into multiple sessions with breaks"
            })
        
        return suggestions

    def calculate_productivity_score(
        self,
        time_entries: List[TimeEntry],
        period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Calculate productivity metrics for a set of time entries.
        """
        if not time_entries:
            return {
                "productivity_score": 0.0,
                "total_hours": 0.0,
                "billable_hours": 0.0,
                "sessions": 0,
                "average_session_length": 0.0,
                "consistency_score": 0.0
            }
        
        total_hours = sum(entry.duration_hours for entry in time_entries)
        billable_hours = sum(entry.duration_hours for entry in time_entries if entry.billable)
        sessions = len(time_entries)
        
        # Calculate average session length
        average_session_length = total_hours / sessions if sessions > 0 else 0
        
        # Calculate consistency (how evenly distributed across days)
        hours_by_day = {}
        for entry in time_entries:
            day = entry.date
            hours_by_day[day] = hours_by_day.get(day, 0) + entry.duration_hours
        
        if len(hours_by_day) > 1:
            daily_hours = list(hours_by_day.values())
            avg_daily = sum(daily_hours) / len(daily_hours)
            variance = sum((h - avg_daily) ** 2 for h in daily_hours) / len(daily_hours)
            consistency_score = max(0, 1 - (variance / (avg_daily ** 2)) if avg_daily > 0 else 0)
        else:
            consistency_score = 1.0 if total_hours > 0 else 0.0
        
        # Calculate overall productivity score
        billable_ratio = billable_hours / total_hours if total_hours > 0 else 0
        session_quality = min(1.0, average_session_length / 2.0)  # Optimal around 2 hours
        
        productivity_score = (
            billable_ratio * 0.4 +  # 40% weight on billable ratio
            session_quality * 0.3 +  # 30% weight on session quality
            consistency_score * 0.3  # 30% weight on consistency
        ) * 100
        
        return {
            "productivity_score": round(productivity_score, 1),
            "total_hours": round(total_hours, 2),
            "billable_hours": round(billable_hours, 2),
            "billable_ratio": round(billable_ratio * 100, 1),
            "sessions": sessions,
            "average_session_length": round(average_session_length, 2),
            "consistency_score": round(consistency_score * 100, 1),
            "days_tracked": len(hours_by_day),
            "hours_by_day": hours_by_day
        }

    def _validate_time_session(self, time_entry: TimeEntry) -> None:
        """
        Validate a time session for business rules.
        """
        # Check minimum duration
        if time_entry.duration_minutes < self.min_session_minutes:
            raise ValidationError(
                f"Session must be at least {self.min_session_minutes} minute(s)",
                "duration"
            )
        
        # Check maximum duration
        if time_entry.duration_hours > self.max_single_session_hours:
            raise ValidationError(
                f"Session cannot exceed {self.max_single_session_hours} hours",
                "duration"
            )
        
        # Check for future dates
        if time_entry.date > datetime.now().date():
            raise ValidationError("Cannot track time for future dates", "date")
        
        # Check for very old dates (more than 1 year)
        one_year_ago = datetime.now().date().replace(year=datetime.now().year - 1)
        if time_entry.date < one_year_ago:
            raise ValidationError("Cannot track time more than 1 year in the past", "date")

    def get_timer_suggestions(
        self,
        user_id: str,
        recent_entries: List[TimeEntry]
    ) -> Dict[str, Any]:
        """
        Get smart suggestions for timer based on recent activity.
        """
        if not recent_entries:
            return {"suggestions": []}
        
        suggestions = []
        
        # Find most common projects
        project_frequency = {}
        for entry in recent_entries[-20:]:  # Last 20 entries
            project_frequency[entry.project_id] = project_frequency.get(entry.project_id, 0) + 1
        
        most_common_projects = sorted(
            project_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        for project_id, frequency in most_common_projects:
            # Find recent tasks for this project
            project_entries = [e for e in recent_entries if e.project_id == project_id]
            recent_tasks = list(set(e.task_id for e in project_entries[-5:] if e.task_id))
            
            suggestions.append({
                "type": "recent_project",
                "project_id": project_id,
                "frequency": frequency,
                "recent_tasks": recent_tasks,
                "last_used": max(e.created_at for e in project_entries).isoformat()
            })
        
        # Detect patterns in work schedule
        current_hour = datetime.now().hour
        current_day = datetime.now().weekday()
        
        similar_time_entries = [
            entry for entry in recent_entries
            if abs(entry.created_at.hour - current_hour) <= 1
            and entry.created_at.weekday() == current_day
        ]
        
        if similar_time_entries:
            most_common_at_this_time = max(
                set(e.project_id for e in similar_time_entries),
                key=lambda x: sum(1 for e in similar_time_entries if e.project_id == x)
            )
            
            suggestions.append({
                "type": "time_pattern",
                "project_id": most_common_at_this_time,
                "reason": f"You often work on this project at this time ({current_hour}:00 on {'weekdays' if current_day < 5 else 'weekends'})"
            })
        
        return {"suggestions": suggestions}