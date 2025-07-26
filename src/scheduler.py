import logging
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import time

# Add the src directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from db_handler import DatabaseHandler
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Scheduler for checking and sending reminders."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize the reminder scheduler.
        
        Args:
            db_path: Optional custom database path
        """
        self.db_path = db_path or Config.DATABASE_PATH
        self.db_handler = DatabaseHandler(self.db_path)
        self.scheduler = BackgroundScheduler()
        self.messenger = None  # Will be set when messenger is implemented
        
        logger.info("Reminder scheduler initialized")
    
    def start(self):
        """Start the scheduler."""
        try:
            # Add the job to run every 5 minutes
            self.scheduler.add_job(
                func=self.check_and_send_reminders,
                trigger=IntervalTrigger(minutes=5),
                id='reminder_check',
                name='Check and send reminders',
                replace_existing=True
            )
            
            self.scheduler.start()
            logger.info("Scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            raise
    
    def stop(self):
        """Stop the scheduler."""
        try:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    def check_and_send_reminders(self):
        """
        Check for due reminders and send them to users.
        This function runs every 5 minutes.
        """
        try:
            current_time = datetime.now()
            logger.info(f"Checking for due reminders at {current_time}")
            
            # Get due reminders based on status and time
            due_reminders = self.db_handler.get_due_reminders_with_status(current_time)
            
            if not due_reminders:
                logger.info("No due reminders found")
                return
            
            logger.info(f"Found {len(due_reminders)} due reminders")
            
            for reminder in due_reminders:
                self._process_reminder(reminder, current_time)
                
        except Exception as e:
            logger.error(f"Error in check_and_send_reminders: {e}")
    
    def _process_reminder(self, reminder: Dict[str, Any], current_time: datetime):
        """
        Process a single reminder.
        
        Args:
            reminder: Dictionary containing reminder data
            current_time: Current datetime
        """
        try:
            event_id = reminder['event_id']
            user_id = reminder['user_id']
            event_summary = reminder['event_summary']
            event_dt = datetime.fromisoformat(reminder['event_dt'])
            status = reminder['status']
            
            # Determine which reminder this is
            reminder_1_dt = reminder.get('reminder_1_dt')
            reminder_2_dt = reminder.get('reminder_2_dt')
            
            if reminder_1_dt:
                reminder_1_dt = datetime.fromisoformat(reminder_1_dt)
            if reminder_2_dt:
                reminder_2_dt = datetime.fromisoformat(reminder_2_dt)
            
            # Check if this is reminder 1 or 2
            is_reminder_1 = (reminder_1_dt and reminder_1_dt <= current_time and status == 'pending')
            is_reminder_2 = (reminder_2_dt and reminder_2_dt <= current_time and status == 'reminded_1')
            
            if is_reminder_1:
                self._send_reminder_1(event_id, user_id, event_summary, event_dt)
            elif is_reminder_2:
                self._send_reminder_2(event_id, user_id, event_summary, event_dt)
            else:
                logger.warning(f"Unexpected reminder state for event {event_id}")
                
        except Exception as e:
            logger.error(f"Error processing reminder for event {reminder.get('event_id')}: {e}")
    
    def _send_reminder_1(self, event_id: int, user_id: str, event_summary: str, event_dt: datetime):
        """
        Send the first reminder for an event.
        
        Args:
            event_id: Event ID
            user_id: User ID to send reminder to
            event_summary: Event summary
            event_dt: Event datetime
        """
        try:
            # Format the reminder message
            message = self._format_reminder_message(event_summary, event_dt, is_first_reminder=True)
            
            # Send the message (placeholder for future messenger integration)
            success = self._send_message_to_user(user_id, message)
            
            if success:
                # Update status to 'reminded_1'
                self.db_handler.update_event(event_id, status='reminded_1')
                logger.info(f"Sent reminder 1 for event {event_id} to user {user_id}")
            else:
                logger.error(f"Failed to send reminder 1 for event {event_id} to user {user_id}")
                
        except Exception as e:
            logger.error(f"Error sending reminder 1 for event {event_id}: {e}")
    
    def _send_reminder_2(self, event_id: int, user_id: str, event_summary: str, event_dt: datetime):
        """
        Send the second reminder for an event.
        
        Args:
            event_id: Event ID
            user_id: User ID to send reminder to
            event_summary: Event summary
            event_dt: Event datetime
        """
        try:
            # Format the reminder message
            message = self._format_reminder_message(event_summary, event_dt, is_first_reminder=False)
            
            # Send the message (placeholder for future messenger integration)
            success = self._send_message_to_user(user_id, message)
            
            if success:
                # Update status to 'reminded_2'
                self.db_handler.update_event(event_id, status='reminded_2')
                logger.info(f"Sent reminder 2 for event {event_id} to user {user_id}")
            else:
                logger.error(f"Failed to send reminder 2 for event {event_id} to user {user_id}")
                
        except Exception as e:
            logger.error(f"Error sending reminder 2 for event {event_id}: {e}")
    
    def _format_reminder_message(self, event_summary: str, event_dt: datetime, is_first_reminder: bool) -> str:
        """
        Format the reminder message.
        
        Args:
            event_summary: Event summary
            event_dt: Event datetime
            is_first_reminder: Whether this is the first or second reminder
            
        Returns:
            Formatted reminder message
        """
        # Calculate time until event
        now = datetime.now()
        time_diff = event_dt - now
        
        if time_diff.days > 0:
            time_str = f"in {time_diff.days} day{'s' if time_diff.days != 1 else ''}"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            time_str = f"in {hours} hour{'s' if hours != 1 else ''}"
        elif time_diff.seconds > 60:
            minutes = time_diff.seconds // 60
            time_str = f"in {minutes} minute{'s' if minutes != 1 else ''}"
        else:
            time_str = "very soon"
        
        # Format the event time
        event_time_str = event_dt.strftime("%Y-%m-%d at %H:%M")
        
        if is_first_reminder:
            return f"🔔 Reminder: {time_str} you have '{event_summary}' on {event_time_str}"
        else:
            return f"⏰ Final Reminder: You have '{event_summary}' on {event_time_str} ({time_str})"
    
    def _send_message_to_user(self, user_id: str, message: str) -> bool:
        """
        Send a message to a user. This is a placeholder for future messenger integration.
        
        Args:
            user_id: User ID to send message to
            message: Message to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            # TODO: Replace this with actual messenger integration
            # For now, just log the message
            logger.info(f"📤 Sending message to user {user_id}: {message}")
            
            # Placeholder for future implementation:
            # if self.messenger:
            #     return self.messenger.send_private_message(user_id, message)
            # else:
            #     logger.warning("Messenger not configured")
            #     return False
            
            # For testing purposes, return True
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {e}")
            return False
    
    def set_messenger(self, messenger):
        """
        Set the messenger instance for sending messages.
        
        Args:
            messenger: Messenger instance with send_private_message method
        """
        self.messenger = messenger
        logger.info("Messenger instance set")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get the current status of the scheduler.
        
        Returns:
            Dictionary with scheduler status information
        """
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            
            return {
                'scheduler_running': self.scheduler.running,
                'jobs': jobs,
                'job_count': len(jobs)
            }
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {'error': str(e)}


# Convenience function for running the scheduler
def run_scheduler(db_path: str = None):
    """
    Run the reminder scheduler.
    
    Args:
        db_path: Optional custom database path
    """
    scheduler = ReminderScheduler(db_path)
    
    try:
        scheduler.start()
        
        # Keep the scheduler running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, stopping scheduler...")
        scheduler.stop()
        logger.info("Scheduler stopped")


# Example usage and testing
if __name__ == "__main__":
    # Run the scheduler
    run_scheduler() 