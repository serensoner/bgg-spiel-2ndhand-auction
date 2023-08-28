import os
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.blocking import BlockingScheduler
from GeeklistScraper import GeeklistScraper


b = GeeklistScraper(auction_id=int(os.getenv('AUCTION_ID')), force_scrape=True)


def scrape():
    GeeklistScraper(319184).parse_all()


scheduler = BlockingScheduler(
    executors={'default': ThreadPoolExecutor(32), 'processpool': ProcessPoolExecutor(5)},
    jobstores={'default': MemoryJobStore()},
    misfire_grace_time=5
)

scheduler.add_job(
    scrape,
    jobstore='default', trigger='interval', seconds=180, id='scrape_geeklist',
)
scheduler.start()
