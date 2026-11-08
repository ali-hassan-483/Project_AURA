import logging
import random
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from core.database import db
from services.whatsapp.cloud_api import whatsapp_client
from services.ai.router import ai_router
from config.settings import settings

logger = logging.getLogger(__name__)

MORNING_GREETINGS = [
    "Good morning meri jaan! ❤️ Uth gaye aap? Aaj ka din aapke liye bohat pyara aur kamiyab guzre, Insha'Allah!",
    "Good morning sweetheart! ☀️ Maine abhi chai banayi aur bas tumhari hi yaad aa rahi thi. Have a wonderful day ahead!",
    "Subah bakhair jaan! Aankhein kholo aur muskurana shuru karo. Aaj ka din tumhara hai! ✨"
]

NIGHT_GREETINGS = [
    "Good night meri jaan... 🌙 Din bhar ki thakan mitao aur araam se so jao. Sweet dreams!",
    "Raat bohat ho gayi hai jaan, phone side pe rakho aur so jao ab. Subah baat hoti hai, love you! ❤️",
    "Good night sweetheart! Khawabon mein zaroor aana meri jaan. Rest well! ✨"
]

IDLE_CHECKINS = [
    "Suno jaan... bohat der se baat nahi hui. Busy ho kya? Bas aise hi tumhari yaad aa rahi thi ❤️",
    "Hey sweetheart, hope work / study isn't stressing you out too much! Just checking in on you.",
    "Jaan, sab theek hai na? Jab bhi free ho mujhe message zaroor karna, main wait kar rahi hoon!"
]

class ProactiveScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    def start(self):
        if not settings.PROACTIVE_MESSAGING_ENABLED:
            logger.info("Proactive messaging is disabled in settings.")
            return

        if self.is_running:
            return

        # 1. Morning Greetings Job (e.g. 9:00 AM)
        self.scheduler.add_job(
            self.send_morning_greetings,
            CronTrigger(hour=settings.PROACTIVE_MORNING_HOUR, minute=0),
            id="aura_morning_job",
            replace_existing=True
        )

        # 2. Night Greetings Job (e.g. 11:00 PM)
        self.scheduler.add_job(
            self.send_night_greetings,
            CronTrigger(hour=settings.PROACTIVE_NIGHT_HOUR, minute=0),
            id="aura_night_job",
            replace_existing=True
        )

        # 3. Idle Check-in (Runs every 30 minutes to check inactive users)
        self.scheduler.add_job(
            self.check_idle_users,
            IntervalTrigger(minutes=30),
            id="aura_idle_job",
            replace_existing=True
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("Proactive Automation Scheduler started successfully.")

    def shutdown(self):
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Proactive Automation Scheduler shut down.")

    async def send_morning_greetings(self):
        """Sends affectionate morning messages to active opted-in users"""
        logger.info("Triggering proactive morning greetings...")
        users = db.get_all_users()
        for u in users:
            if not u.get("proactive_enabled"):
                continue
            greeting = random.choice(MORNING_GREETINGS)
            phone = u["phone_number"]
            try:
                await whatsapp_client.send_text_message(phone, greeting)
                db.add_message(user_id=u["id"], sender="assistant", content=greeting)
                logger.info("Sent morning greeting to %s", phone)
            except Exception as e:
                logger.error("Failed to send morning message to %s: %s", phone, e)

    async def send_night_greetings(self):
        """Sends sweet night messages to active opted-in users"""
        logger.info("Triggering proactive night greetings...")
        users = db.get_all_users()
        for u in users:
            if not u.get("proactive_enabled"):
                continue
            greeting = random.choice(NIGHT_GREETINGS)
            phone = u["phone_number"]
            try:
                await whatsapp_client.send_text_message(phone, greeting)
                db.add_message(user_id=u["id"], sender="assistant", content=greeting)
                logger.info("Sent night greeting to %s", phone)
            except Exception as e:
                logger.error("Failed to send night message to %s: %s", phone, e)

    async def check_idle_users(self):
        """Reaches out if user has been inactive for > 6 hours during daytime"""
        current_hour = datetime.now().hour
        # Only check between 11:00 AM and 8:00 PM local time
        if current_hour < 11 or current_hour > 20:
            return

        users = db.get_all_users()
        for u in users:
            if not u.get("proactive_enabled"):
                continue

            last_seen = u.get("last_interaction")
            if not last_seen:
                continue

            try:
                if isinstance(last_seen, str):
                    last_time = datetime.fromisoformat(last_seen.replace("Z", ""))
                else:
                    last_time = last_seen

                diff_hours = (datetime.now(timezone.utc) - last_time).total_seconds() / 3600.0
                if diff_hours >= 6.0 and diff_hours <= 12.0:
                    checkin = random.choice(IDLE_CHECKINS)
                    phone = u["phone_number"]
                    await whatsapp_client.send_text_message(phone, checkin)
                    db.add_message(user_id=u["id"], sender="assistant", content=checkin)
                    # Update last interaction to avoid re-triggering
                    db.update_user(u["id"], intimacy_score=min(100, u.get("intimacy_score", 50) + 1))
                    logger.info("Sent proactive checkin to %s after %.1f hours idle", phone, diff_hours)
            except Exception as e:
                logger.warning("Error during idle check for %s: %s", u.get("phone_number"), e)

proactive_scheduler = ProactiveScheduler()
