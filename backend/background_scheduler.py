import schedule
import time
import logging
import threading
from scraping_service import run_scraping_sync

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackgroundScheduler:
    def __init__(self):
        self.running = False
        self.scraping_in_progress = False
        self.thread = None

    def run_scraping_job(self):
        """Run the scraping job"""
        if self.scraping_in_progress:
            logger.warning("Scraping already in progress, skipping...")
            return

        self.scraping_in_progress = True
        logger.info("Starting scheduled scraping job...")
        try:
            result = run_scraping_sync()
            logger.info(f"Scraping job completed: {result}")
        except Exception as e:
            logger.error(f"Scraping job failed: {e}")
        finally:
            self.scraping_in_progress = False

    def setup_schedule(self):
        """Set up the scraping schedule"""
        # Run scraping every 2 hours
        schedule.every(2).hours.do(self.run_scraping_job)

        # Also run once daily at 6 AM
        schedule.every().day.at("06:00").do(self.run_scraping_job)

        logger.info("Background scheduler set up - scraping every 2 hours and daily at 6 AM")

    def start(self):
        """Start the background scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.setup_schedule()
        self.running = True

        def run_scheduler():
            logger.info("Background scheduler started")
            # Run first scrape 5 minutes after startup
            time.sleep(300)
            if self.running:
                logger.info("Running initial scrape after startup...")
                self.run_scraping_job()
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            logger.info("Background scheduler stopped")

        self.thread = threading.Thread(target=run_scheduler, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the background scheduler"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Background scheduler stopped")

    def run_immediate_scraping(self):
        """Run scraping immediately (for testing)"""
        return self.run_scraping_job()

# Global scheduler instance
scheduler = BackgroundScheduler()

def start_scheduler():
    """Start the global scheduler"""
    scheduler.start()

def stop_scheduler():
    """Stop the global scheduler"""
    scheduler.stop()

def run_immediate_scraping():
    """Run immediate scraping"""
    return scheduler.run_immediate_scraping()
