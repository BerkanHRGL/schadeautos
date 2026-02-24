import smtplib
import logging
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.models import User, UserPreference, Car, Notification
from decouple import config
from jinja2 import Template

class NotificationService:
    def __init__(self):
        self.smtp_server = config("SMTP_SERVER", default="smtp.gmail.com")
        self.smtp_port = config("SMTP_PORT", default=587, cast=int)
        self.email_address = config("EMAIL_ADDRESS", default="")
        self.email_password = config("EMAIL_PASSWORD", default="")
        self.logger = logging.getLogger(__name__)

    async def send_new_cars_notifications(self, db: Session):
        """Send notifications to users about new cars matching their preferences"""
        if not config("ENABLE_EMAIL_NOTIFICATIONS", default=True, cast=bool):
            return

        # Get users with email notifications enabled
        users = db.query(User).join(UserPreference).filter(
            UserPreference.email_notifications == True
        ).all()

        for user in users:
            try:
                await self._send_user_notifications(user, db)
            except Exception as e:
                self.logger.error(f"Error sending notifications to user {user.email}: {e}")

    async def _send_user_notifications(self, user: User, db: Session):
        """Send notifications to a specific user"""
        preferences = user.preferences
        if not preferences:
            return

        # Get cars added in the last hour that match user preferences
        recent_cars = self._get_matching_cars(user, db)

        if not recent_cars:
            return

        # Group notifications by frequency
        if preferences.notification_frequency == "instant":
            for car in recent_cars:
                await self._send_single_car_notification(user, car, db)
        elif preferences.notification_frequency == "daily":
            await self._send_daily_digest(user, recent_cars, db)
        elif preferences.notification_frequency == "weekly":
            await self._send_weekly_digest(user, recent_cars, db)

    def _get_matching_cars(self, user: User, db: Session) -> List[Car]:
        """Get cars that match user preferences"""
        preferences = user.preferences
        if not preferences:
            return []

        # Base query for active cars with cosmetic damage
        query = db.query(Car).filter(
            Car.is_active == True,
            Car.has_cosmetic_damage_only == True
        )

        # Filter by preferences
        if preferences.max_price:
            query = query.filter(Car.price <= preferences.max_price)

        if preferences.min_price:
            query = query.filter(Car.price >= preferences.min_price)

        if preferences.max_mileage:
            query = query.filter(Car.mileage <= preferences.max_mileage)

        if preferences.min_year:
            query = query.filter(Car.year >= preferences.min_year)

        if preferences.max_year:
            query = query.filter(Car.year <= preferences.max_year)

        if preferences.preferred_makes:
            query = query.filter(Car.make.in_(preferences.preferred_makes))

        # Filter by notification frequency
        if preferences.notification_frequency == "instant":
            time_threshold = datetime.utcnow() - timedelta(hours=1)
        elif preferences.notification_frequency == "daily":
            time_threshold = datetime.utcnow() - timedelta(days=1)
        else:  # weekly
            time_threshold = datetime.utcnow() - timedelta(days=7)

        query = query.filter(Car.first_seen >= time_threshold)

        # Exclude cars already notified
        notified_car_ids = db.query(Notification.car_id).filter(
            Notification.user_id == user.id,
            Notification.notification_type == "new_match"
        ).subquery()

        query = query.filter(~Car.id.in_(notified_car_ids))

        return query.limit(50).all()

    async def _send_single_car_notification(self, user: User, car: Car, db: Session):
        """Send notification for a single car"""
        subject = f"New Car Match: {car.make} {car.model or ''} - €{car.price:,.0f}"

        template = Template("""
        <h2>New Car Found!</h2>
        <p>We found a new car that matches your preferences:</p>

        <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <h3>{{ car.make }} {{ car.model or '' }} ({{ car.year or 'Unknown' }})</h3>
            <p><strong>Price:</strong> €{{ "{:,.0f}".format(car.price) if car.price else 'Contact seller' }}</p>
            <p><strong>Mileage:</strong> {{ "{:,}".format(car.mileage) if car.mileage else 'Unknown' }} km</p>
            <p><strong>Location:</strong> {{ car.location or 'Not specified' }}</p>
            <p><strong>Damage:</strong> {{ car.damage_description or 'See listing' }}</p>
            <p><strong>Source:</strong> {{ car.source_website }}</p>
            <p><a href="{{ car.url }}" style="background: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 3px;">View Listing</a></p>
        </div>

        <p>Best regards,<br>Car Damage Finder</p>
        """)

        body = template.render(car=car)

        await self._send_email(user.email, subject, body)

        # Create notification record
        notification = Notification(
            user_id=user.id,
            car_id=car.id,
            notification_type="new_match",
            title=subject,
            message=f"New car match: {car.make} {car.model or ''}"
        )
        db.add(notification)
        db.commit()

    async def _send_daily_digest(self, user: User, cars: List[Car], db: Session):
        """Send daily digest of new cars"""
        if not cars:
            return

        subject = f"Daily Car Digest - {len(cars)} New Matches"

        template = Template("""
        <h2>Your Daily Car Digest</h2>
        <p>We found {{ cars|length }} new cars that match your preferences:</p>

        {% for car in cars %}
        <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <h3>{{ car.make }} {{ car.model or '' }} ({{ car.year or 'Unknown' }})</h3>
            <p><strong>Price:</strong> €{{ "{:,.0f}".format(car.price) if car.price else 'Contact seller' }}</p>
            <p><strong>Mileage:</strong> {{ "{:,}".format(car.mileage) if car.mileage else 'Unknown' }} km</p>
            <p><strong>Source:</strong> {{ car.source_website }}</p>
            <p><a href="{{ car.url }}">View Listing</a></p>
        </div>
        {% endfor %}

        <p>Best regards,<br>Car Damage Finder</p>
        """)

        body = template.render(cars=cars)

        await self._send_email(user.email, subject, body)

        # Create digest notification record
        notification = Notification(
            user_id=user.id,
            notification_type="daily_digest",
            title=subject,
            message=f"Daily digest with {len(cars)} new car matches"
        )
        db.add(notification)
        db.commit()

    async def _send_weekly_digest(self, user: User, cars: List[Car], db: Session):
        """Send weekly digest of new cars"""
        if not cars:
            return

        subject = f"Weekly Car Digest - {len(cars)} New Matches"

        # Similar to daily digest but with weekly context
        template = Template("""
        <h2>Your Weekly Car Digest</h2>
        <p>Here's a summary of {{ cars|length }} new cars from this week that match your preferences:</p>

        {% for car in cars %}
        <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <h3>{{ car.make }} {{ car.model or '' }} ({{ car.year or 'Unknown' }})</h3>
            <p><strong>Price:</strong> €{{ "{:,.0f}".format(car.price) if car.price else 'Contact seller' }}</p>
            <p><strong>Mileage:</strong> {{ "{:,}".format(car.mileage) if car.mileage else 'Unknown' }} km</p>
            <p><strong>Source:</strong> {{ car.source_website }}</p>
            <p><strong>Added:</strong> {{ car.first_seen.strftime('%Y-%m-%d %H:%M') }}</p>
            <p><a href="{{ car.url }}">View Listing</a></p>
        </div>
        {% endfor %}

        <p>Best regards,<br>Car Damage Finder</p>
        """)

        body = template.render(cars=cars)

        await self._send_email(user.email, subject, body)

        # Create digest notification record
        notification = Notification(
            user_id=user.id,
            notification_type="weekly_digest",
            title=subject,
            message=f"Weekly digest with {len(cars)} new car matches"
        )
        db.add(notification)
        db.commit()

    async def _send_email(self, to_email: str, subject: str, body: str):
        """Send email using SMTP"""
        if not self.email_address or not self.email_password:
            self.logger.warning("Email credentials not configured")
            return

        try:
            msg = MimeMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_address
            msg['To'] = to_email

            # Create HTML part
            html_part = MimeText(body, 'html')
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                text = msg.as_string()
                server.sendmail(self.email_address, to_email, text)

            self.logger.info(f"Email sent successfully to {to_email}")

        except Exception as e:
            self.logger.error(f"Failed to send email to {to_email}: {e}")

    async def send_test_notification(self, user_email: str) -> bool:
        """Send test notification to verify email configuration"""
        subject = "Car Damage Finder - Test Notification"
        body = """
        <h2>Test Notification</h2>
        <p>This is a test email to verify that your notification settings are working correctly.</p>
        <p>If you received this email, your notification preferences are properly configured!</p>
        <p>Best regards,<br>Car Damage Finder Team</p>
        """

        try:
            await self._send_email(user_email, subject, body)
            return True
        except Exception as e:
            self.logger.error(f"Test notification failed: {e}")
            return False