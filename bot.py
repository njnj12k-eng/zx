# -*- coding: utf-8 -*-
"""
Ghost Assistant Bot - Complete Telegram Bot System
Version: 1.0.0
Last Update: 1405/04/22
"""

import asyncio
import logging
import json
import uuid
import hashlib
import re
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal

# Third-party imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum, JSON, BigInteger, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import IntegrityError
import redis
from redis import Redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from cryptography.fernet import Fernet

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
class Config:
    TOKEN = "8961040480:AAHNKEnK7LZuCp9fSJ5td2_XdGFqPtwp_dY"
    DATABASE_URL = "sqlite:///ghost_bot.db"
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    ENCRYPTION_KEY = Fernet.generate_key()
    TIMEZONE = "Asia/Tehran"
    
    # Admin Users (Telegram IDs)
    OWNER_IDS = ["8961040480"]  # Replace with actual owner IDs
    ADMIN_IDS = ["8961040480"]  # Add other admin IDs
    
    # Default settings
    DEFAULT_LANGUAGE = "fa"
    DIAMOND_PRICE = 8000  # IRR per diamond
    GIFT_DIAMONDS = 31
    MAINTENANCE_MODE = False
    MAINTENANCE_MESSAGE = "🛠 ربات در حال بروزرسانی است. زمان تقریبی: 15 دقیقه"
    
    # Premium Plans (in days and diamonds)
    PREMIUM_PLANS = {
        "1_month": {"days": 30, "diamonds": 40, "price": 50000},
        "2_month": {"days": 60, "diamonds": 60, "price": 90000},
        "4_month": {"days": 120, "diamonds": 100, "price": 150000},
        "8_month": {"days": 240, "diamonds": 130, "price": 200000},
        "12_month": {"days": 365, "diamonds": 180, "price": 350000}
    }
    
    # Diamond Purchase Packs
    DIAMOND_PACKS = {
        10: 80000,
        25: 180000,
        50: 350000,
        100: 650000,
        250: 1500000,
        500: 2800000
    }
    
    # Bank Card Information
    BANK_CARD = {
        "number": "6037-9918-1234-5678",
        "owner": "Ali Rezaei",
        "bank": "Melli"
    }
    
    # Ad Prices
    AD_PRICE = 250000  # Monthly ad price
    
    # Rate Limits
    RATE_LIMIT = {
        "messages_per_second": 5,
        "withdraw_per_day": 3,
        "max_invoices": 10,
        "failed_attempts": 5
    }

# ==================== DATABASE MODELS ====================
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone_number = Column(String(20))
    language = Column(String(5), default=Config.DEFAULT_LANGUAGE)
    role = Column(String(20), default='user')  # owner, admin, finance_admin, ads_admin, user
    is_verified = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    premium_expire = Column(DateTime)
    diamonds_balance = Column(Integer, default=0)
    gifted_diamonds = Column(Integer, default=0)
    wallet_balance = Column(Float, default=0.0)
    last_activity = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="user", lazy='dynamic')
    invoices = relationship("Invoice", back_populates="user", lazy='dynamic')
    purchases = relationship("Purchase", back_populates="user", lazy='dynamic')
    ads = relationship("Ad", back_populates="user", lazy='dynamic')
    audit_logs = relationship("AuditLog", back_populates="user", lazy='dynamic')
    broadcasts = relationship("Broadcast", back_populates="creator", lazy='dynamic')

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id'))
    type = Column(String(20))  # purchase, withdraw, gift, refund, premium, ad, system
    status = Column(String(20), default='pending')  # pending, completed, failed, cancelled
    amount = Column(Float, default=0)
    diamonds_amount = Column(Integer, default=0)
    description = Column(Text)
    reference_id = Column(String(100))
    balance_before = Column(Float)
    balance_after = Column(Float)
    diamonds_before = Column(Integer)
    diamonds_after = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    
    user = relationship("User", back_populates="transactions")
    audit_logs = relationship("AuditLog", back_populates="transaction", lazy='dynamic')

class Invoice(Base):
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(50), unique=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    amount = Column(Float)
    description = Column(Text)
    card_number = Column(String(20))
    sender_card = Column(String(20))
    receipt_image = Column(String(200))
    status = Column(String(20), default='pending')  # pending, verified, rejected
    verified_by = Column(Integer, ForeignKey('users.id'))
    verified_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", foreign_keys=[user_id])
    verifier = relationship("User", foreign_keys=[verified_by])

class Purchase(Base):
    __tablename__ = 'purchases'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id'))
    plan_type = Column(String(20))
    duration_days = Column(Integer)
    diamonds_cost = Column(Integer)
    amount = Column(Float)
    status = Column(String(20), default='pending')
    started_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="purchases")

class Ad(Base):
    __tablename__ = 'ads'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id'))
    content = Column(Text)
    media_type = Column(String(20))  # text, photo, video
    media_id = Column(String(200))
    plan_type = Column(String(20))
    price = Column(Float)
    status = Column(String(20), default='pending')  # pending, active, completed, cancelled
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    started_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", back_populates="ads")

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id'))
    transaction_id = Column(Integer, ForeignKey('transactions.id'))
    action = Column(String(100))
    description = Column(Text)
    ip_address = Column(String(50))
    user_agent = Column(String(200))
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="audit_logs")
    transaction = relationship("Transaction", back_populates="audit_logs")

class Broadcast(Base):
    __tablename__ = 'broadcasts'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    content = Column(Text)
    media_type = Column(String(20))
    media_id = Column(String(200))
    target_users = Column(Text)  # JSON array or "all"
    sent_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    status = Column(String(20), default='pending')
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now)
    sent_at = Column(DateTime)
    
    creator = relationship("User", back_populates="broadcasts")

class SystemSetting(Base):
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True)
    value = Column(Text)
    category = Column(String(50))
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# Create database
engine = create_engine(Config.DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# ==================== REDIS MANAGER ====================
class RedisManager:
    def __init__(self):
        try:
            self.client = Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                decode_responses=True
            )
        except:
            self.client = None
            logger.warning("Redis not available, using fallback")
    
    def get(self, key: str) -> Optional[str]:
        if self.client:
            return self.client.get(key)
        return None
    
    def set(self, key: str, value: str, expire: int = None):
        if self.client:
            if expire:
                self.client.setex(key, expire, value)
            else:
                self.client.set(key, value)
    
    def delete(self, key: str):
        if self.client:
            self.client.delete(key)
    
    def incr(self, key: str) -> int:
        if self.client:
            return self.client.incr(key)
        return 0
    
    def exists(self, key: str) -> bool:
        if self.client:
            return self.client.exists(key) > 0
        return False
    
    def hset(self, name: str, key: str, value: str):
        if self.client:
            self.client.hset(name, key, value)
    
    def hget(self, name: str, key: str) -> Optional[str]:
        if self.client:
            return self.client.hget(name, key)
        return None
    
    def hgetall(self, name: str) -> Dict:
        if self.client:
            return self.client.hgetall(name)
        return {}

# ==================== UTILITY FUNCTIONS ====================
class Utils:
    @staticmethod
    def generate_invoice_number() -> str:
        return f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    @staticmethod
    def format_price(amount: float) -> str:
        return f"{amount:,.0f}".replace(',', '٫')
    
    @staticmethod
    def get_expiry_date(days: int) -> datetime:
        return datetime.now() + timedelta(days=days)
    
    @staticmethod
    def validate_card_number(card: str) -> bool:
        card = re.sub(r'\D', '', card)
        if not card.isdigit() or len(card) != 16:
            return False
        total = 0
        for i, digit in enumerate(reversed(card)):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        return total % 10 == 0
    
    @staticmethod
    def generate_uuid() -> str:
        return str(uuid.uuid4())

# ==================== TRANSLATION SYSTEM ====================
class I18n:
    translations = {
        'fa': {
            'welcome_new': "🎉 به ربات Ghost Assistant خوش آمدید!\n\n"
                          "💎 شما {gift} الماس هدیه دریافت کردید.\n"
                          "از منوی زیر استفاده کنید:",
            'welcome_back': "👋 خوش برگشتید!\n"
                           "از منوی زیر استفاده کنید:",
            'menu_header': "📋 *منوی اصلی*\n"
                          "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            'profile': "👤 *پروفایل کاربری*\n\n"
                      "🆔 شناسه: {id}\n"
                      "👤 نام: {name}\n"
                      "🌐 زبان: {lang}\n"
                      "💎 الماس: {diamonds}\n"
                      "  ├─ هدیه: {gifted}\n"
                      "  └─ خریداری: {purchased}\n"
                      "⭐ پریمیوم: {premium}\n"
                      "💰 کیف پول: {wallet:,} تومان\n"
                      "📅 عضو از: {joined}",
            'diamonds_shop': "💎 *خرید الماس*\n\n"
                           "💰 قیمت هر الماس: {price:,} تومان\n"
                           "💎 موجودی شما: {balance}\n\n"
                           "📦 پکیج‌های ویژه:",
            'premium_plans': "⭐ *اشتراک پریمیوم*\n\n"
                           "💎 الماس مورد نیاز:\n"
                           "{plans}\n"
                           "💎 موجودی شما: {balance}\n"
                           "⭐ وضعیت: {status}",
            'wallet': "💰 *کیف پول*\n\n"
                     "💎 الماس: {diamonds}\n"
                     "💰 موجودی ریال: {wallet:,} تومان\n\n"
                     "📊 آخرین تراکنش‌ها:\n{transactions}",
            'payment': "💳 *پرداخت*\n\n"
                      "🏦 اطلاعات واریز:\n"
                      "شماره کارت: `{card}`\n"
                      "بانک: {bank}\n"
                      "صاحب حساب: {owner}\n\n"
                      "📝 دستورالعمل:\n"
                      "۱. مبلغ را واریز کنید\n"
                      "۲. رسید را ارسال کنید\n"
                      "۳. شماره کارت مبدا را اعلام کنید",
            'maintenance': "🛠 ربات در حال بروزرسانی است.\n"
                          "زمان تقریبی: 15 دقیقه",
            'rate_limit': "⏳ لطفاً کمی صبر کنید.\n"
                         "سرعت درخواست‌های شما بالاست.",
            'language_changed': "🌐 زبان شما به {lang} تغییر کرد.",
            'admin_required': "⛔ این دستور فقط برای ادمین‌ها قابل استفاده است.",
            'owner_required': "⛔ این دستور فقط برای مالک اصلی است.",
            'user_not_found': "❌ کاربر یافت نشد.",
            'success': "✅ عملیات با موفقیت انجام شد.",
            'failed': "❌ عملیات ناموفق بود.",
            'pending': "⏳ در حال انتظار برای تایید.",
            'invoice_created': "🧾 فاکتور ایجاد شد.\n"
                              "شماره فاکتور: {number}\n"
                              "مبلغ: {amount:,} تومان\n"
                              "وضعیت: در انتظار تایید",
            'premium_activated': "⭐ اشتراک پریمیوم شما فعال شد!\n"
                               "اعتبار تا: {expire}",
            'diamonds_purchased': "💎 {amount} الماس به حساب شما اضافه شد.",
            'withdraw_request': "🏦 درخواست برداشت ثبت شد.\n"
                              "مبلغ: {amount:,} تومان\n"
                              "وضعیت: در انتظار بررسی",
            'insufficient_diamonds': "❌ الماس کافی ندارید!\n"
                                    "نیاز: {need} 💎\n"
                                    "موجودی: {balance} 💎",
            'no_invoices': "📋 هیچ فاکتوری ثبت نشده است.",
            'receipt_received': "✅ رسید شما دریافت شد.\n"
                              "پس از تایید ادمین، الماس به حساب شما اضافه می‌شود.",
            'receipt_error': "❌ فاکتور در انتظار پرداختی یافت نشد.",
            'broadcast_sent': "✅ Broadcast ارسال شد!\n"
                            "تعداد کل: {total}\n"
                            "ارسال شده: {sent}",
            'backup_created': "🔄 بکاپ ایجاد شد.\n"
                             "📅 {date}",
            'version': "🤖 Ghost Assistant\n"
                      "نسخه: {version}\n"
                      "آخرین بروزرسانی: {update}",
            'help_text': "📚 *راهنمای ربات*\n\n"
                        "/start - شروع و منوی اصلی\n"
                        "/menu - منوی اصلی\n"
                        "/profile - پروفایل کاربری\n"
                        "/wallet - کیف پول\n"
                        "/diamonds - خرید الماس\n"
                        "/premium - اشتراک پریمیوم\n"
                        "/payment - پرداخت\n"
                        "/invoice - فاکتورها\n"
                        "/history - تاریخچه تراکنش‌ها\n"
                        "/settings - تنظیمات\n"
                        "/language - تغییر زبان\n"
                        "/support - پشتیبانی\n"
                        "/ads - تبلیغات\n"
                        "/ai - هوش مصنوعی"
        },
        'en': {
            'welcome_new': "🎉 Welcome to Ghost Assistant!\n\n"
                          "💎 You received {gift} diamonds as a gift.\n"
                          "Use the menu below:",
            'welcome_back': "👋 Welcome back!\n"
                           "Use the menu below:",
            'menu_header': "📋 *Main Menu*\n"
                          "Please select an option:",
            'profile': "👤 *User Profile*\n\n"
                      "🆔 ID: {id}\n"
                      "👤 Name: {name}\n"
                      "🌐 Language: {lang}\n"
                      "💎 Diamonds: {diamonds}\n"
                      "  ├─ Gifted: {gifted}\n"
                      "  └─ Purchased: {purchased}\n"
                      "⭐ Premium: {premium}\n"
                      "💰 Wallet: {wallet:,} IRR\n"
                      "📅 Joined: {joined}",
            'diamonds_shop': "💎 *Diamond Shop*\n\n"
                           "💰 Price per diamond: {price:,} IRR\n"
                           "💎 Your balance: {balance}\n\n"
                           "📦 Special packs:",
            'premium_plans': "⭐ *Premium Subscription*\n\n"
                           "💎 Diamonds required:\n"
                           "{plans}\n"
                           "💎 Your balance: {balance}\n"
                           "⭐ Status: {status}",
            'wallet': "💰 *Wallet*\n\n"
                     "💎 Diamonds: {diamonds}\n"
                     "💰 IRR Balance: {wallet:,}\n\n"
                     "📊 Recent transactions:\n{transactions}",
            'payment': "💳 *Payment*\n\n"
                      "🏦 Transfer information:\n"
                      "Card Number: `{card}`\n"
                      "Bank: {bank}\n"
                      "Account Holder: {owner}\n\n"
                      "📝 Instructions:\n"
                      "1. Transfer the amount\n"
                      "2. Send receipt\n"
                      "3. Provide sender card number",
            'maintenance': "🛠 Bot is under maintenance.\n"
                          "Estimated time: 15 minutes",
            'rate_limit': "⏳ Please wait a moment.\n"
                         "Your request rate is too high.",
            'language_changed': "🌐 Your language changed to {lang}.",
            'admin_required': "⛔ This command is only for admins.",
            'owner_required': "⛔ This command is only for the owner.",
            'user_not_found': "❌ User not found.",
            'success': "✅ Operation successful.",
            'failed': "❌ Operation failed.",
            'pending': "⏳ Waiting for confirmation.",
            'invoice_created': "🧾 Invoice created.\n"
                              "Invoice Number: {number}\n"
                              "Amount: {amount:,} IRR\n"
                              "Status: Pending",
            'premium_activated': "⭐ Your premium subscription activated!\n"
                               "Expires: {expire}",
            'diamonds_purchased': "💎 {amount} diamonds added to your account.",
            'withdraw_request': "🏦 Withdrawal request submitted.\n"
                              "Amount: {amount:,} IRR\n"
                              "Status: Pending review",
            'insufficient_diamonds': "❌ Insufficient diamonds!\n"
                                    "Need: {need} 💎\n"
                                    "Balance: {balance} 💎",
            'no_invoices': "📋 No invoices found.",
            'receipt_received': "✅ Receipt received.\n"
                              "After admin verification, diamonds will be added.",
            'receipt_error': "❌ No pending invoice found.",
            'broadcast_sent': "✅ Broadcast sent!\n"
                            "Total: {total}\n"
                            "Sent: {sent}",
            'backup_created': "🔄 Backup created.\n"
                             "📅 {date}",
            'version': "🤖 Ghost Assistant\n"
                      "Version: {version}\n"
                      "Last Update: {update}",
            'help_text': "📚 *Bot Help*\n\n"
                        "/start - Start and main menu\n"
                        "/menu - Main menu\n"
                        "/profile - User profile\n"
                        "/wallet - Wallet\n"
                        "/diamonds - Buy diamonds\n"
                        "/premium - Premium subscription\n"
                        "/payment - Payment\n"
                        "/invoice - Invoices\n"
                        "/history - Transaction history\n"
                        "/settings - Settings\n"
                        "/language - Change language\n"
                        "/support - Support\n"
                        "/ads - Ads\n"
                        "/ai - AI Assistant"
        }
    }
    
    @staticmethod
    def get_text(key: str, lang: str = 'fa', **kwargs) -> str:
        translations = I18n.translations.get(lang, I18n.translations['fa'])
        text = translations.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except:
                return text
        return text

# ==================== DATABASE MANAGER ====================
class DBManager:
    @staticmethod
    def get_user(telegram_id: str) -> Optional[User]:
        session = Session()
        try:
            return session.query(User).filter_by(telegram_id=telegram_id).first()
        except:
            return None
        finally:
            session.close()
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        session = Session()
        try:
            return session.query(User).filter_by(id=user_id).first()
        except:
            return None
        finally:
            session.close()
    
    @staticmethod
    def create_user(telegram_id: str, username: str = None, 
                   first_name: str = None, last_name: str = None) -> User:
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                return user
            
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                diamonds_balance=Config.GIFT_DIAMONDS,
                gifted_diamonds=Config.GIFT_DIAMONDS,
                created_at=datetime.now()
            )
            
            # Check if this is the owner
            if telegram_id in Config.OWNER_IDS:
                user.role = 'owner'
            
            session.add(user)
            session.commit()
            
            # Create welcome transaction
            transaction = Transaction(
                user_id=user.id,
                type='gift',
                status='completed',
                diamonds_amount=Config.GIFT_DIAMONDS,
                description='هدیه ثبت‌نام / Welcome gift',
                diamonds_before=0,
                diamonds_after=Config.GIFT_DIAMONDS,
                completed_at=datetime.now()
            )
            session.add(transaction)
            
            # Audit log
            audit = AuditLog(
                user_id=user.id,
                action='register',
                description='New user registered',
                details={'gifted_diamonds': Config.GIFT_DIAMONDS}
            )
            session.add(audit)
            session.commit()
            
            logger.info(f"New user registered: {telegram_id}")
            return user
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating user: {e}")
            raise
        finally:
            session.close()
    
    @staticmethod
    def update_user_balance(user_id: int, diamonds: int = None, wallet: float = None):
        session = Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return None
            
            if diamonds is not None:
                user.diamonds_balance += diamonds
            if wallet is not None:
                user.wallet_balance += wallet
            
            user.updated_at = datetime.now()
            session.commit()
            return user
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating user balance: {e}")
            raise
        finally:
            session.close()
    
    @staticmethod
    def create_transaction(user_id: int, type: str, amount: float = 0, 
                          diamonds_amount: int = 0, description: str = None,
                          reference_id: str = None) -> Transaction:
        session = Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError("User not found")
            
            transaction = Transaction(
                user_id=user_id,
                type=type,
                status='pending',
                amount=amount,
                diamonds_amount=diamonds_amount,
                description=description,
                reference_id=reference_id,
                balance_before=user.wallet_balance,
                diamonds_before=user.diamonds_balance
            )
            session.add(transaction)
            session.commit()
            return transaction
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating transaction: {e}")
            raise
        finally:
            session.close()
    
    @staticmethod
    def complete_transaction(transaction_id: int, status: str = 'completed'):
        session = Session()
        try:
            transaction = session.query(Transaction).filter_by(id=transaction_id).first()
            if not transaction:
                raise ValueError("Transaction not found")
            
            transaction.status = status
            transaction.completed_at = datetime.now()
            
            if status == 'completed':
                user = session.query(User).filter_by(id=transaction.user_id).first()
                if user:
                    if transaction.diamonds_amount:
                        user.diamonds_balance += transaction.diamonds_amount
                    if transaction.amount:
                        user.wallet_balance += transaction.amount
                    
                    transaction.diamonds_after = user.diamonds_balance
                    transaction.balance_after = user.wallet_balance
            
            session.commit()
            return transaction
        except Exception as e:
            session.rollback()
            logger.error(f"Error completing transaction: {e}")
            raise
        finally:
            session.close()

# ==================== MAIN BOT CLASS ====================
class GhostBot:
    def __init__(self, token: str):
        self.token = token
        self.redis = RedisManager()
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone(Config.TIMEZONE))
        
        # Conversation states
        self.WAITING_FOR_BROADCAST = 1
        self.WAITING_FOR_RECEIPT = 2
        self.WAITING_FOR_WITHDRAW = 3
        self.WAITING_FOR_CARD = 4
        
        self.application = ApplicationBuilder().token(token).build()
        self.setup_handlers()
        self.setup_scheduled_jobs()
        
        logger.info("Bot initialized successfully")
    
    def setup_handlers(self):
        """Register all handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("menu", self.menu_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("wallet", self.wallet_command))
        self.application.add_handler(CommandHandler("diamonds", self.diamonds_command))
        self.application.add_handler(CommandHandler("premium", self.premium_command))
        self.application.add_handler(CommandHandler("payment", self.payment_command))
        self.application.add_handler(CommandHandler("invoice", self.invoice_command))
        self.application.add_handler(CommandHandler("history", self.history_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("language", self.language_command))
        self.application.add_handler(CommandHandler("support", self.support_command))
        self.application.add_handler(CommandHandler("ads", self.ads_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("broadcast", self.broadcast_command))
        self.application.add_handler(CommandHandler("backup", self.backup_command))
        self.application.add_handler(CommandHandler("ai", self.ai_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("version", self.version_command))
        self.application.add_handler(CommandHandler("cancel", self.cancel_command))
        
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(self.callback_handler))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_handler))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.photo_handler))
        self.application.add_handler(MessageHandler(filters.VOICE, self.voice_handler))
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.document_handler))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    def setup_scheduled_jobs(self):
        """Setup scheduled jobs"""
        self.scheduler.add_job(
            self.daily_backup,
            CronTrigger(hour=2, minute=0),
            id='daily_backup'
        )
        
        self.scheduler.add_job(
            self.cleanup_expired_premium,
            CronTrigger(hour=3, minute=0),
            id='cleanup_premium'
        )
        
        self.scheduler.add_job(
            self.update_ad_stats,
            CronTrigger(hour='*/6'),
            id='update_ads'
        )
        
        self.scheduler.start()
        logger.info("Scheduled jobs started")
    
    # ==================== COMMAND HANDLERS ====================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        if await self.is_maintenance_mode() and str(user.id) not in Config.OWNER_IDS:
            await update.message.reply_text(I18n.get_text('maintenance'))
            return
        
        db_user = DBManager.create_user(
            str(user.id),
            user.username,
            user.first_name,
            user.last_name
        )
        
        lang = db_user.language
        
        if db_user.created_at.date() == datetime.now().date():
            welcome = I18n.get_text('welcome_new', lang, gift=Config.GIFT_DIAMONDS)
        else:
            welcome = I18n.get_text('welcome_back', lang)
        
        keyboard = [
            [InlineKeyboardButton("💎 الماس", callback_data="diamonds"),
             InlineKeyboardButton("⭐ پریمیوم", callback_data="premium")],
            [InlineKeyboardButton("💰 کیف پول", callback_data="wallet"),
             InlineKeyboardButton("👤 پروفایل", callback_data="profile")],
            [InlineKeyboardButton("📢 تبلیغات", callback_data="ads"),
             InlineKeyboardButton("🤖 هوش مصنوعی", callback_data="ai")],
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"),
             InlineKeyboardButton("📊 تاریخچه", callback_data="history")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command"""
        user = await self.get_or_create_user(update)
        
        keyboard = [
            [InlineKeyboardButton("💎 الماس", callback_data="diamonds"),
             InlineKeyboardButton("⭐ پریمیوم", callback_data="premium")],
            [InlineKeyboardButton("💰 کیف پول", callback_data="wallet"),
             InlineKeyboardButton("👤 پروفایل", callback_data="profile")],
            [InlineKeyboardButton("📊 تاریخچه", callback_data="history"),
             InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            I18n.get_text('menu_header', user.language),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /profile command"""
        user = await self.get_or_create_user(update)
        
        premium_status = "✅ فعال" if user.is_premium else "❌ غیرفعال"
        if user.is_premium and user.premium_expire:
            expire_date = user.premium_expire.strftime('%Y/%m/%d')
            premium_status += f"\n⏳ اعتبار تا: {expire_date}"
        
        profile_text = I18n.get_text('profile', user.language,
            id=user.telegram_id,
            name=user.first_name or 'نامشخص',
            lang=user.language,
            diamonds=user.diamonds_balance,
            gifted=user.gifted_diamonds,
            purchased=user.diamonds_balance - user.gifted_diamonds,
            premium=premium_status,
            wallet=user.wallet_balance,
            joined=user.created_at.strftime('%Y/%m/%d')
        )
        
        keyboard = [
            [InlineKeyboardButton("💎 خرید الماس", callback_data="buy_diamonds"),
             InlineKeyboardButton("⭐ فعال‌سازی پریمیوم", callback_data="buy_premium")],
            [InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            profile_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def wallet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /wallet command"""
        user = await self.get_or_create_user(update)
        
        session = Session()
        try:
            transactions = session.query(Transaction).filter_by(
                user_id=user.id
            ).order_by(Transaction.created_at.desc()).limit(5).all()
            
            tx_text = ""
            if transactions:
                for tx in transactions:
                    status_emoji = "✅" if tx.status == "completed" else "⏳" if tx.status == "pending" else "❌"
                    tx_text += f"\n{status_emoji} {tx.type}: {tx.amount:,.0f} تومان"
                    tx_text += f"\n   📅 {tx.created_at.strftime('%Y/%m/%d %H:%M')}"
            else:
                tx_text = "هیچ تراکنشی ثبت نشده است."
            
            wallet_text = I18n.get_text('wallet', user.language,
                diamonds=user.diamonds_balance,
                wallet=user.wallet_balance,
                transactions=tx_text
            )
        finally:
            session.close()
        
        keyboard = [
            [InlineKeyboardButton("💳 شارژ کیف پول", callback_data="charge_wallet"),
             InlineKeyboardButton("🏦 برداشت", callback_data="withdraw")],
            [InlineKeyboardButton("📋 گردش کامل", callback_data="full_history"),
             InlineKeyboardButton("💎 خرید الماس", callback_data="buy_diamonds")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            wallet_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def diamonds_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /diamonds command"""
        user = await self.get_or_create_user(update)
        
        diamonds_text = I18n.get_text('diamonds_shop', user.language,
            price=Config.DIAMOND_PRICE,
            balance=user.diamonds_balance
        )
        
        keyboard = []
        packs = list(Config.DIAMOND_PACKS.items())
        for i in range(0, len(packs), 2):
            row = []
            for j in range(i, min(i+2, len(packs))):
                amount, price = packs[j]
                row.append(InlineKeyboardButton(
                    f"{amount} 💎 {price:,}تومان",
                    callback_data=f"buy_diamonds_{amount}"
                ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔄 تبدیل به اشتراک", callback_data="premium")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            diamonds_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def premium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /premium command"""
        user = await self.get_or_create_user(update)
        
        plans_text = ""
        for plan, data in Config.PREMIUM_PLANS.items():
            plans_text += f"• {data['days']} روز = {data['diamonds']} 💎\n"
        
        premium_status = "✅ فعال" if user.is_premium else "❌ غیرفعال"
        if user.is_premium and user.premium_expire:
            premium_status += f"\n⏳ اعتبار تا: {user.premium_expire.strftime('%Y/%m/%d')}"
        
        premium_text = I18n.get_text('premium_plans', user.language,
            plans=plans_text,
            balance=user.diamonds_balance,
            status=premium_status
        )
        
        keyboard = [
            [InlineKeyboardButton("۱ ماه (۴۰💎)", callback_data="premium_1_month"),
             InlineKeyboardButton("۲ ماه (۶۰💎)", callback_data="premium_2_month")],
            [InlineKeyboardButton("۴ ماه (۱۰۰💎)", callback_data="premium_4_month"),
             InlineKeyboardButton("۸ ماه (۱۳۰💎)", callback_data="premium_8_month")],
            [InlineKeyboardButton("۱ سال (۱۸۰💎)", callback_data="premium_12_month")],
            [InlineKeyboardButton("💳 خرید نقدی", callback_data="buy_premium_cash")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            premium_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def payment_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /payment command"""
        user = await self.get_or_create_user(update)
        
        payment_text = I18n.get_text('payment', user.language,
            card=Config.BANK_CARD['number'],
            bank=Config.BANK_CARD['bank'],
            owner=Config.BANK_CARD['owner']
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 کپی شماره کارت", callback_data="copy_card")],
            [InlineKeyboardButton("📤 ارسال رسید پرداخت", callback_data="send_receipt")],
            [InlineKeyboardButton("📋 مشاهده فاکتورها", callback_data="view_invoices")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            payment_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def invoice_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /invoice command"""
        user = await self.get_or_create_user(update)
        
        session = Session()
        try:
            invoices = session.query(Invoice).filter_by(
                user_id=user.id
            ).order_by(Invoice.created_at.desc()).limit(10).all()
            
            if not invoices:
                await update.message.reply_text(I18n.get_text('no_invoices', user.language))
                return
            
            invoice_text = "📋 *فاکتورهای شما:*\n\n"
            for inv in invoices:
                status_emoji = "✅" if inv.status == "verified" else "⏳" if inv.status == "pending" else "❌"
                invoice_text += f"{status_emoji} فاکتور #{inv.invoice_number}\n"
                invoice_text += f"   مبلغ: {inv.amount:,.0f} تومان\n"
                invoice_text += f"   وضعیت: {inv.status}\n"
                invoice_text += f"   📅 {inv.created_at.strftime('%Y/%m/%d %H:%M')}\n\n"
            
            await update.message.reply_text(
                invoice_text,
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            session.close()
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command"""
        user = await self.get_or_create_user(update)
        
        session = Session()
        try:
            transactions = session.query(Transaction).filter_by(
                user_id=user.id
            ).order_by(Transaction.created_at.desc()).limit(20).all()
            
            if not transactions:
                await update.message.reply_text("📊 هیچ تراکنشی ثبت نشده است.")
                return
            
            history_text = "📊 *تاریخچه تراکنش‌ها*\n"
            history_text += f"کل تراکنش‌ها: {len(transactions)}\n\n"
            
            for tx in transactions:
                status_emoji = "✅" if tx.status == "completed" else "⏳" if tx.status == "pending" else "❌"
                history_text += f"{status_emoji} {tx.type}: {tx.amount:,.0f} تومان\n"
                if tx.diamonds_amount:
                    history_text += f"   💎 {tx.diamonds_amount} الماس\n"
                history_text += f"   🆔 {tx.uuid[:12]}...\n"
                history_text += f"   📅 {tx.created_at.strftime('%Y/%m/%d %H:%M')}\n"
                if tx.description:
                    history_text += f"   📝 {tx.description}\n"
                history_text += "\n"
            
            await update.message.reply_text(
                history_text,
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            session.close()
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        user = await self.get_or_create_user(update)
        
        keyboard = [
            [InlineKeyboardButton("🌐 زبان / Language", callback_data="language")],
            [InlineKeyboardButton("⏰ تنظیمات تاخیر", callback_data="delay_setting")],
            [InlineKeyboardButton("🔔 اعلان‌ها", callback_data="notifications")],
            [InlineKeyboardButton("🕐 نمایش ساعت", callback_data="show_time")],
            [InlineKeyboardButton("🌙 حالت شب", callback_data="night_mode")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚙️ *تنظیمات شخصی*\n"
            "تنظیمات خود را انتخاب کنید:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /language command"""
        user = await self.get_or_create_user(update)
        
        keyboard = [
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
             InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🌐 *انتخاب زبان / Select Language*",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def support_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /support command"""
        await update.message.reply_text(
            "📞 *پشتیبانی*\n\n"
            "برای ارتباط با پشتیبانی، از راه‌های زیر استفاده کنید:\n"
            "📧 ایمیل: support@ghostbot.com\n"
            "🆔 تلگرام: @GhostSupport\n\n"
            "ساعات پاسخگویی: ۹ صبح تا ۱۱ شب",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def ads_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ads command"""
        user = await self.get_or_create_user(update)
        
        ads_text = (
            "📢 *سیستم تبلیغات*\n\n"
            f"💰 هزینه ماهانه: {Config.AD_PRICE:,} تومان\n"
            "📊 آمار: نمایش کلیک و بازدید\n"
            "⏳ مدت: ۳۰ روز\n\n"
            "📝 برای ثبت تبلیغ، مراحل زیر را انجام دهید:\n"
            "۱. مبلغ را به شماره کارت واریز کنید\n"
            "۲. رسید را ارسال کنید\n"
            "۳. متن تبلیغ خود را ارسال کنید\n"
            "۴. پس از تایید ادمین، تبلیغ فعال می‌شود"
        )
        
        keyboard = [
            [InlineKeyboardButton("📝 ثبت تبلیغ جدید", callback_data="register_ad")],
            [InlineKeyboardButton("📊 آمار تبلیغات من", callback_data="my_ads_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            ads_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command"""
        user_id = str(update.effective_user.id)
        
        if not await self.is_admin(user_id):
            await update.message.reply_text(I18n.get_text('admin_required'))
            return
        
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            lang = user.language if user else 'fa'
            
            keyboard = [
                [InlineKeyboardButton("👑 مدیریت کاربران", callback_data="admin_users")],
                [InlineKeyboardButton("💎 مدیریت قیمت الماس", callback_data="admin_diamond_price")],
                [InlineKeyboardButton("🏦 مدیریت شماره کارت", callback_data="admin_bank_card")],
                [InlineKeyboardButton("🎁 مدیریت هدیه ثبت‌نام", callback_data="admin_gift")],
                [InlineKeyboardButton("✅ تایید پرداخت‌ها", callback_data="admin_verify_payments")],
                [InlineKeyboardButton("📢 مدیریت تبلیغات", callback_data="admin_ads")],
                [InlineKeyboardButton("📊 آمار درآمد", callback_data="admin_stats")],
                [InlineKeyboardButton("🔄 بکاپ", callback_data="admin_backup")],
                [InlineKeyboardButton("📋 لاگ عملیات", callback_data="admin_audit_log")],
                [InlineKeyboardButton("🛠 حالت نگهداری", callback_data="admin_maintenance")],
                [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
                [InlineKeyboardButton("📋 تنظیمات سیستم", callback_data="admin_settings")]
            ]
            
            # Show version info
            if user.role == 'owner':
                keyboard.append([InlineKeyboardButton("📌 نسخه سیستم", callback_data="admin_version")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "👑 *پنل مدیریت*\n"
                "سیستم Ghost Assistant\n"
                f"نسخه: ۱.۰.۰\n"
                f"آخرین بروزرسانی: ۱۴۰۵/۰۴/۲۲",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            session.close()
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user_id = str(update.effective_user.id)
        
        if not await self.is_admin(user_id):
            await update.message.reply_text(I18n.get_text('admin_required'))
            return
        
        session = Session()
        try:
            total_users = session.query(User).count()
            premium_users = session.query(User).filter_by(is_premium=True).count()
            total_transactions = session.query(Transaction).filter_by(status='completed').count()
            
            total_revenue = session.query(Transaction).filter_by(
                status='completed'
            ).filter(Transaction.type.in_(['purchase', 'premium', 'ad'])).with_entities(
                func.sum(Transaction.amount)
            ).scalar() or 0
            
            today = datetime.now().date()
            daily_revenue = session.query(Transaction).filter(
                Transaction.status == 'completed',
                Transaction.created_at >= today
            ).with_entities(func.sum(Transaction.amount)).scalar() or 0
            
            month_start = today.replace(day=1)
            monthly_revenue = session.query(Transaction).filter(
                Transaction.status == 'completed',
                Transaction.created_at >= month_start
            ).with_entities(func.sum(Transaction.amount)).scalar() or 0
            
            total_diamonds = session.query(User).with_entities(func.sum(User.diamonds_balance)).scalar() or 0
            
            stats_text = (
                "📊 *آمار کلی سیستم*\n\n"
                "👥 *کاربران*\n"
                f"• کل: {total_users}\n"
                f"• پریمیوم: {premium_users}\n\n"
                "💰 *درآمد*\n"
                f"• امروز: {daily_revenue:,.0f} تومان\n"
                f"• این ماه: {monthly_revenue:,.0f} تومان\n"
                f"• کل: {total_revenue:,.0f} تومان\n\n"
                "💎 *الماس*\n"
                f"• کل در گردش: {total_diamonds}\n\n"
                "📋 *تراکنش‌ها*\n"
                f"• کل: {total_transactions}\n"
                f"• در انتظار: {session.query(Transaction).filter_by(status='pending').count()}\n\n"
                f"📅 امروز: {today.strftime('%Y/%m/%d')}"
            )
            
            await update.message.reply_text(
                stats_text,
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            session.close()
    
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /broadcast command"""
        user_id = str(update.effective_user.id)
        
        if not await self.is_admin(user_id):
            await update.message.reply_text(I18n.get_text('admin_required'))
            return
        
        context.user_data['broadcast_step'] = True
        await update.message.reply_text(
            "📢 *ارسال Broadcast*\n\n"
            "لطفاً پیام خود را ارسال کنید:\n"
            "(می‌توانید متن، عکس یا فایل ارسال کنید)\n\n"
            "برای لغو، /cancel را بفرستید.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def backup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /backup command"""
        user_id = str(update.effective_user.id)
        
        if not await self.is_admin(user_id):
            await update.message.reply_text(I18n.get_text('admin_required'))
            return
        
        try:
            backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2("ghost_bot.db", backup_file)
            
            with open(backup_file, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=backup_file,
                    caption=I18n.get_text('backup_created', 'fa',
                        date=datetime.now().strftime('%Y/%m/%d %H:%M'))
                )
            
            os.remove(backup_file)
            
            await self.log_audit(
                user_id,
                'backup',
                'Database backup created'
            )
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در ایجاد بکاپ: {str(e)}")
    
    async def ai_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ai command"""
        user = await self.get_or_create_user(update)
        
        await update.message.reply_text(
            "🤖 *هوش مصنوعی Ghost*\n\n"
            "قابلیت‌ها:\n"
            "• پاسخ هوشمند به سوالات\n"
            "• ترجمه متون\n"
            "• تبدیل ویس به متن\n"
            "• خلاصه‌سازی گفتگو\n\n"
            "برای استفاده، سوال خود را بپرسید.\n"
            "مثال: /ai بهترین ربات تلگرام چیست؟",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user = await self.get_or_create_user(update)
        help_text = I18n.get_text('help_text', user.language)
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def version_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /version command"""
        user = await self.get_or_create_user(update)
        version_text = I18n.get_text('version', user.language,
            version="۱.۰.۰",
            update="۱۴۰۵/۰۴/۲۲"
        )
        await update.message.reply_text(version_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command"""
        context.user_data.clear()
        await update.message.reply_text("✅ عملیات لغو شد.")
    
    # ==================== CALLBACK HANDLER ====================
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        data = query.data
        
        if await self.is_maintenance_mode() and user_id not in Config.OWNER_IDS:
            await query.edit_message_text(I18n.get_text('maintenance'))
            return
        
        # Handle different callbacks
        if data == "diamonds":
            await self.diamonds_command(update, context)
        elif data == "premium":
            await self.premium_command(update, context)
        elif data == "wallet":
            await self.wallet_command(update, context)
        elif data == "profile":
            await self.profile_command(update, context)
        elif data == "settings":
            await self.settings_command(update, context)
        elif data == "history":
            await self.history_command(update, context)
        elif data == "ads":
            await self.ads_command(update, context)
        elif data == "ai":
            await self.ai_command(update, context)
        elif data == "language":
            await self.language_command(update, context)
        elif data.startswith("lang_"):
            lang = data.split("_")[1]
            await self.change_language(user_id, lang, query)
        elif data.startswith("buy_diamonds_"):
            amount = int(data.split("_")[2])
            await self.buy_diamonds(user_id, amount, query)
        elif data.startswith("premium_"):
            plan = data.split("_")[1]
            await self.buy_premium(user_id, plan, query)
        elif data == "copy_card":
            await query.edit_message_text(
                f"📋 *شماره کارت*\n\n"
                f"`{Config.BANK_CARD['number']}`\n\n"
                f"✅ کپی شد!",
                parse_mode=ParseMode.MARKDOWN
            )
        elif data == "buy_premium_cash":
            await self.buy_premium_cash(user_id, query)
        elif data == "charge_wallet":
            await self.charge_wallet(user_id, query)
        elif data == "withdraw":
            await self.withdraw_request(user_id, query)
        elif data == "send_receipt":
            context.user_data['receipt_step'] = True
            await query.edit_message_text(
                "📤 لطفاً رسید پرداخت خود را به صورت عکس ارسال کنید.\n"
                "همچنین شماره کارت مبدا را همراه با رسید ارسال کنید."
            )
        elif data == "view_invoices":
            await self.invoice_command(update, context)
        elif data == "refresh_profile":
            await self.profile_command(update, context)
        elif data == "buy_diamonds":
            await self.diamonds_command(update, context)
        elif data == "buy_premium":
            await self.premium_command(update, context)
        elif data == "full_history":
            await self.history_command(update, context)
        elif data.startswith("admin_"):
            await self.handle_admin_actions(user_id, data, query)
        elif data.startswith("verify_"):
            await self.verify_payment(user_id, data, query)
        elif data.startswith("reject_"):
            await self.reject_payment(user_id, data, query)
        elif data.startswith("ad_approve_"):
            await self.approve_ad(user_id, data, query)
        elif data.startswith("ad_reject_"):
            await self.reject_ad(user_id, data, query)
        elif data == "register_ad":
            await self.register_ad(user_id, query)
        elif data == "my_ads_stats":
            await self.my_ads_stats(user_id, query)
    
    # ==================== BUSINESS LOGIC ====================
    
    async def get_or_create_user(self, update: Update) -> User:
        """Get or create user from update"""
        user = update.effective_user
        return DBManager.create_user(
            str(user.id),
            user.username,
            user.first_name,
            user.last_name
        )
    
    async def is_admin(self, user_id: str) -> bool:
        """Check if user is admin"""
        if user_id in Config.OWNER_IDS:
            return True
        
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            return user and user.role in ['owner', 'admin', 'finance_admin', 'ads_admin']
        finally:
            session.close()
    
    async def is_owner(self, user_id: str) -> bool:
        """Check if user is owner"""
        return user_id in Config.OWNER_IDS
    
    async def is_maintenance_mode(self) -> bool:
        """Check if maintenance mode is enabled"""
        session = Session()
        try:
            setting = session.query(SystemSetting).filter_by(key='maintenance_mode').first()
            return setting and setting.value == 'true'
        finally:
            session.close()
    
    async def log_audit(self, user_id: str, action: str, description: str, details: Dict = None):
        """Log admin action for audit"""
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                return
            
            audit = AuditLog(
                user_id=user.id,
                action=action,
                description=description,
                details=details or {},
                created_at=datetime.now()
            )
            session.add(audit)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging audit: {e}")
        finally:
            session.close()
    
    async def change_language(self, user_id: str, lang: str, query):
        """Change user language"""
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if user:
                user.language = lang
                session.commit()
                
                await query.edit_message_text(
                    I18n.get_text('language_changed', lang, lang=lang)
                )
        finally:
            session.close()
    
    async def buy_diamonds(self, user_id: str, amount: int, query):
        """Process diamond purchase"""
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                await query.edit_message_text(I18n.get_text('user_not_found'))
                return
            
            price = Config.DIAMOND_PACKS.get(amount)
            if not price:
                await query.edit_message_text("❌ پکیج نامعتبر")
                return
            
            invoice_number = Utils.generate_invoice_number()
            invoice = Invoice(
                invoice_number=invoice_number,
                user_id=user.id,
                amount=price,
                description=f"خرید {amount} الماس",
                status='pending',
                created_at=datetime.now()
            )
            session.add(invoice)
            session.commit()
            
            transaction = DBManager.create_transaction(
                user.id,
                'purchase',
                amount=price,
                diamonds_amount=amount,
                description=f"خرید {amount} الماس",
                reference_id=invoice_number
            )
            
            payment_text = (
                f"🧾 *فاکتور خرید الماس*\n\n"
                f"شماره فاکتور: `{invoice_number}`\n"
                f"تعداد الماس: {amount} 💎\n"
                f"مبلغ: {price:,} تومان\n"
                f"وضعیت: در انتظار پرداخت\n\n"
                f"لطفاً مبلغ را به شماره کارت زیر واریز کنید:\n"
                f"`{Config.BANK_CARD['number']}`\n\n"
                f"پس از واریز، رسید را ارسال کنید."
            )
            
            keyboard = [
                [InlineKeyboardButton("📤 ارسال رسید", callback_data="send_receipt")],
                [InlineKeyboardButton("📋 مشاهده فاکتورها", callback_data="view_invoices")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                payment_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            await self.log_audit(
                user_id,
                'diamond_purchase',
                f'Purchased {amount} diamonds',
                {'amount': amount, 'price': price, 'invoice': invoice_number}
            )
        except Exception as e:
            session.rollback()
            await query.edit_message_text(f"❌ خطا: {str(e)}")
        finally:
            session.close()
    
    async def buy_premium(self, user_id: str, plan: str, query):
        """Process premium purchase with diamonds"""
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                await query.edit_message_text(I18n.get_text('user_not_found'))
                return
            
            plan_data = Config.PREMIUM_PLANS.get(plan)
            if not plan_data:
                await query.edit_message_text("❌ پلن نامعتبر")
                return
            
            if user.diamonds_balance < plan_data['diamonds']:
                await query.edit_message_text(
                    I18n.get_text('insufficient_diamonds', user.language,
                        need=plan_data['diamonds'],
                        balance=user.diamonds_balance
                    )
                )
                return
            
            # Deduct diamonds
            user.diamonds_balance -= plan_data['diamonds']
            
            # Activate premium
            user.is_premium = True
            user.premium_expire = Utils.get_expiry_date(plan_data['days'])
            
            purchase = Purchase(
                uuid=Utils.generate_uuid(),
                user_id=user.id,
                plan_type=plan,
                duration_days=plan_data['days'],
                diamonds_cost=plan_data['diamonds'],
                amount=plan_data['price'],
                status='completed',
                started_at=datetime.now(),
                expires_at=user.premium_expire,
                created_at=datetime.now()
            )
            session.add(purchase)
            
            transaction = Transaction(
                uuid=Utils.generate_uuid(),
                user_id=user.id,
                type='premium',
                status='completed',
                diamonds_amount=-plan_data['diamonds'],
                description=f"فعال‌سازی پریمیوم {plan_data['days']} روزه",
                diamonds_before=user.diamonds_balance + plan_data['diamonds'],
                diamonds_after=user.diamonds_balance,
                completed_at=datetime.now()
            )
            session.add(transaction)
            
            session.commit()
            
            await self.log_audit(
                user_id,
                'premium_activation',
                f'Activated premium for {plan_data["days"]} days',
                {'plan': plan, 'days': plan_data['days'], 'cost': plan_data['diamonds']}
            )
            
            await query.edit_message_text(
                I18n.get_text('premium_activated', user.language,
                    expire=user.premium_expire.strftime('%Y/%m/%d')
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            session.rollback()
            await query.edit_message_text(f"❌ خطا: {str(e)}")
        finally:
            session.close()
    
    async def buy_premium_cash(self, user_id: str, query):
        """Process premium purchase with cash"""
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                await query.edit_message_text(I18n.get_text('user_not_found'))
                return
            
            plans_text = ""
            for plan, data in Config.PREMIUM_PLANS.items():
                plans_text += f"• {data['days']} روز = {data['price']:,} تومان\n"
            
            keyboard = []
            for plan, data in Config.PREMIUM_PLANS.items():
                keyboard.append([
                    InlineKeyboardButton(
                        f"{data['days']} روز - {data['price']:,} تومان",
                        callback_data=f"cash_premium_{plan}"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"⭐ *خرید نقدی پریمیوم*\n\n"
                f"پلن‌های موجود:\n{plans_text}\n"
                f"پس از انتخاب، فاکتور برای شما صادر می‌شود.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            session.close()
    
    async def charge_wallet(self, user_id: str, query):
        """Process wallet charge"""
        await query.edit_message_text(
            "💰 *شارژ کیف پول*\n\n"
            "لطفاً مبلغ مورد نظر را به تومان وارد کنید:\n"
            "(حداقل مبلغ: ۱۰,۰۰۰ تومان)\n\n"
            "برای لغو، /cancel را بفرستید."
        )
    
    async def withdraw_request(self, user_id: str, query):
        """Process withdrawal request"""
        await query.edit_message_text(
            "🏦 *درخواست برداشت*\n\n"
            "لطفاً مبلغ مورد نظر را به تومان وارد کنید:\n"
            "(حداکثر ۳ درخواست در روز)\n\n"
            "برای لغو، /cancel را بفرستید."
        )
    
    async def verify_payment(self, user_id: str, data: str, query):
        """Verify payment"""
        invoice_id = int(data.split("_")[1])
        
        if not await self.is_admin(user_id):
            await query.edit_message_text(I18n.get_text('admin_required'))
            return
        
        session = Session()
        try:
            invoice = session.query(Invoice).filter_by(id=invoice_id).first()
            if not invoice:
                await query.edit_message_text("❌ فاکتور یافت نشد.")
                return
            
            user = session.query(User).filter_by(id=invoice.user_id).first()
            
            # Update invoice
            invoice.status = 'verified'
            invoice.verified_by = session.query(User).filter_by(telegram_id=user_id).first().id
            invoice.verified_at = datetime.now()
            
            # Add diamonds to user if it's a diamond purchase
            if 'الماس' in invoice.description:
                import re
                match = re.search(r'(\d+)', invoice.description)
                if match:
                    diamonds = int(match.group(1))
                    user.diamonds_balance += diamonds
                    
                    transaction = Transaction(
                        uuid=Utils.generate_uuid(),
                        user_id=user.id,
                        type='purchase',
                        status='completed',
                        amount=invoice.amount,
                        diamonds_amount=diamonds,
                        description=invoice.description,
                        diamonds_before=user.diamonds_balance - diamonds,
                        diamonds_after=user.diamonds_balance,
                        completed_at=datetime.now()
                    )
                    session.add(transaction)
            
            session.commit()
            
            await self.log_audit(
                user_id,
                'verify_payment',
                f'Verified payment {invoice.invoice_number}',
                {'invoice': invoice.invoice_number, 'amount': invoice.amount}
            )
            
            await query.edit_message_text(
                f"✅ پرداخت تایید شد!\n"
                f"فاکتور: {invoice.invoice_number}\n"
                f"کاربر: {user.telegram_id}\n"
                f"مبلغ: {invoice.amount:,.0f} تومان"
            )
            
            # Notify user
            try:
                await self.application.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"✅ پرداخت شما تایید شد!\n"
                         f"فاکتور: {invoice.invoice_number}\n"
                         f"مبلغ: {invoice.amount:,.0f} تومان"
                )
            except:
                pass
                
        except Exception as e:
            session.rollback()
            await query.edit_message_text(f"❌ خطا: {str(e)}")
        finally:
            session.close()
    
    async def reject_payment(self, user_id: str, data: str, query):
        """Reject payment"""
        invoice_id = int(data.split("_")[1])
        
        if not await self.is_admin(user_id):
            await query.edit_message_text(I18n.get_text('admin_required'))
            return
        
        session = Session()
        try:
            invoice = session.query(Invoice).filter_by(id=invoice_id).first()
            if not invoice:
                await query.edit_message_text("❌ فاکتور یافت نشد.")
                return
            
            user = session.query(User).filter_by(id=invoice.user_id).first()
            
            invoice.status = 'rejected'
            invoice.verified_by = session.query(User).filter_by(telegram_id=user_id).first().id
            invoice.verified_at = datetime.now()
            session.commit()
            
            await self.log_audit(
                user_id,
                'reject_payment',
                f'Rejected payment {invoice.invoice_number}',
                {'invoice': invoice.invoice_number, 'amount': invoice.amount}
            )
            
            await query.edit_message_text(
                f"❌ پرداخت رد شد!\n"
                f"فاکتور: {invoice.invoice_number}"
            )
            
            # Notify user
            try:
                await self.application.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"❌ پرداخت شما رد شد.\n"
                         f"فاکتور: {invoice.invoice_number}\n"
                         f"لطفاً با پشتیبانی تماس بگیرید."
                )
            except:
                pass
                
        except Exception as e:
            session.rollback()
            await query.edit_message_text(f"❌ خطا: {str(e)}")
        finally:
            session.close()
    
    async def approve_ad(self, user_id: str, data: str, query):
        """Approve ad"""
        ad_id = int(data.split("_")[2])
        
        if not await self.is_admin(user_id):
            await query.edit_message_text(I18n.get_text('admin_required'))
            return
        
        session = Session()
        try:
            ad = session.query(Ad).filter_by(id=ad_id).first()
            if not ad:
                await query.edit_message_text("❌ تبلیغ یافت نشد.")
                return
            
            ad.status = 'active'
            ad.started_at = datetime.now()
            ad.expires_at = datetime.now() + timedelta(days=30)
            session.commit()
            
            await self.log_audit(
                user_id,
                'approve_ad',
                f'Approved ad {ad.uuid}',
                {'ad_id': ad.id}
            )
            
            await query.edit_message_text("✅ تبلیغ تایید و فعال شد!")
            
        except Exception as e:
            session.rollback()
            await query.edit_message_text(f"❌ خطا: {str(e)}")
        finally:
            session.close()
    
    async def reject_ad(self, user_id: str, data: str, query):
        """Reject ad"""
        ad_id = int(data.split("_")[2])
        
        if not await self.is_admin(user_id):
            await query.edit_message_text(I18n.get_text('admin_required'))
            return
        
        session = Session()
        try:
            ad = session.query(Ad).filter_by(id=ad_id).first()
            if not ad:
                await query.edit_message_text("❌ تبلیغ یافت نشد.")
                return
            
            ad.status = 'rejected'
            session.commit()
            
            await self.log_audit(
                user_id,
                'reject_ad',
                f'Rejected ad {ad.uuid}',
                {'ad_id': ad.id}
            )
            
            await query.edit_message_text("❌ تبلیغ رد شد.")
            
        except Exception as e:
            session.rollback()
            await query.edit_message_text(f"❌ خطا: {str(e)}")
        finally:
            session.close()
    
    async def register_ad(self, user_id: str, query):
        """Register new ad"""
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                await query.edit_message_text(I18n.get_text('user_not_found'))
                return
            
            # Create invoice for ad
            invoice_number = Utils.generate_invoice_number()
            invoice = Invoice(
                invoice_number=invoice_number,
                user_id=user.id,
                amount=Config.AD_PRICE,
                description="ثبت تبلیغ ماهانه",
                status='pending',
                created_at=datetime.now()
            )
            session.add(invoice)
            session.commit()
            
            await query.edit_message_text(
                f"📢 *ثبت تبلیغ*\n\n"
                f"هزینه ماهانه: {Config.AD_PRICE:,} تومان\n"
                f"شماره فاکتور: `{invoice_number}`\n\n"
                f"لطفاً مبلغ را به شماره کارت زیر واریز کنید:\n"
                f"`{Config.BANK_CARD['number']}`\n\n"
                f"پس از واریز، رسید را ارسال کنید.\n"
                f"سپس متن تبلیغ خود را ارسال کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            session.rollback()
            await query.edit_message_text(f"❌ خطا: {str(e)}")
        finally:
            session.close()
    
    async def my_ads_stats(self, user_id: str, query):
        """Show user's ad statistics"""
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                await query.edit_message_text(I18n.get_text('user_not_found'))
                return
            
            ads = session.query(Ad).filter_by(user_id=user.id).all()
            
            if not ads:
                await query.edit_message_text("📊 شما هیچ تبلیغی ثبت نکرده‌اید.")
                return
            
            stats_text = "📊 *آمار تبلیغات شما*\n\n"
            for ad in ads:
                stats_text += f"🆔 {ad.uuid[:8]}\n"
                stats_text += f"📝 {ad.content[:50]}...\n"
                stats_text += f"👁 بازدید: {ad.views}\n"
                stats_text += f"🖱 کلیک: {ad.clicks}\n"
                stats_text += f"📅 {ad.created_at.strftime('%Y/%m/%d')}\n"
                stats_text += f"وضعیت: {ad.status}\n"
                stats_text += "---\n"
            
            await query.edit_message_text(
                stats_text,
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            session.close()
    
    # ==================== ADMIN FUNCTIONS ====================
    
    async def handle_admin_actions(self, user_id: str, data: str, query):
        """Handle admin panel actions"""
        if not await self.is_admin(user_id):
            await query.edit_message_text(I18n.get_text('admin_required'))
            return
        
        action = data.split("_")[1]
        
        if action == "users":
            await self.admin_users(user_id, query)
        elif action == "diamond_price":
            await self.admin_diamond_price(user_id, query)
        elif action == "bank_card":
            await self.admin_bank_card(user_id, query)
        elif action == "gift":
            await self.admin_gift(user_id, query)
        elif action == "verify_payments":
            await self.admin_verify_payments(user_id, query)
        elif action == "ads":
            await self.admin_ads(user_id, query)
        elif action == "stats":
            await self.admin_stats(user_id, query)
        elif action == "backup":
            await self.admin_backup(user_id, query)
        elif action == "audit_log":
            await self.admin_audit_log(user_id, query)
        elif action == "maintenance":
            await self.admin_maintenance(user_id, query)
        elif action == "broadcast":
            await self.admin_broadcast(user_id, query)
        elif action == "settings":
            await self.admin_settings(user_id, query)
        elif action == "version":
            await self.admin_version(user_id, query)
    
    async def admin_users(self, user_id: str, query):
        """Admin: Manage users"""
        session = Session()
        try:
            users = session.query(User).order_by(User.created_at.desc()).limit(20).all()
            
            users_text = "👑 *مدیریت کاربران*\n\n"
            for user in users:
                users_text += f"🆔 {user.telegram_id}\n"
                users_text += f"👤 {user.first_name or 'نامشخص'}\n"
                users_text += f"💎 {user.diamonds_balance} | ⭐ {'✅' if user.is_premium else '❌'}\n"
                users_text += f"📅 {user.created_at.strftime('%Y/%m/%d')}\n"
                users_text += "---\n"
            
            keyboard = [
                [InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search_user")],
                [InlineKeyboardButton("📊 آمار کاربران", callback_data="admin_user_stats")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                users_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            session.close()
    
    async def admin_diamond_price(self, user_id: str, query):
        """Admin: Change diamond price"""
        await query.edit_message_text(
            f"💎 *تنظیم قیمت الماس*\n\n"
            f"قیمت فعلی: {Config.DIAMOND_PRICE:,} تومان\n\n"
            "برای تغییر، قیمت جدید را وارد کنید:\n"
            "(عدد را به تومان وارد کنید)"
        )
    
    async def admin_bank_card(self, user_id: str, query):
        """Admin: Change bank card"""
        await query.edit_message_text(
            f"🏦 *مدیریت شماره کارت*\n\n"
            f"شماره کارت فعلی: `{Config.BANK_CARD['number']}`\n"
            f"بانک: {Config.BANK_CARD['bank']}\n"
            f"صاحب حساب: {Config.BANK_CARD['owner']}\n\n"
            "برای تغییر، شماره کارت جدید را وارد کنید:"
        )
    
    async def admin_gift(self, user_id: str, query):
        """Admin: Change gift diamonds"""
        await query.edit_message_text(
            f"🎁 *مدیریت هدیه ثبت‌نام*\n\n"
            f"مقدار فعلی: {Config.GIFT_DIAMONDS} الماس\n\n"
            "مقدار جدید را وارد کنید:"
        )
    
    async def admin_verify_payments(self, user_id: str, query):
        """Admin: Verify pending payments"""
        session = Session()
        try:
            pending_invoices = session.query(Invoice).filter_by(
                status='pending'
            ).order_by(Invoice.created_at).limit(10).all()
            
            if not pending_invoices:
                await query.edit_message_text("✅ هیچ پرداخت در انتظار تاییدی وجود ندارد.")
                return
            
            invoices_text = "✅ *تایید پرداخت‌ها*\n\n"
            for inv in pending_invoices:
                user = session.query(User).filter_by(id=inv.user_id).first()
                invoices_text += f"🧾 فاکتور: {inv.invoice_number}\n"
                invoices_text += f"👤 کاربر: {user.telegram_id if user else 'نامشخص'}\n"
                invoices_text += f"💰 مبلغ: {inv.amount:,.0f} تومان\n"
                invoices_text += f"📝 {inv.description}\n"
                invoices_text += "---\n"
            
            keyboard = []
            for inv in pending_invoices[:5]:
                keyboard.append([
                    InlineKeyboardButton(f"✅ تایید {inv.invoice_number}", callback_data=f"verify_{inv.id}"),
                    InlineKeyboardButton(f"❌ رد", callback_data=f"reject_{inv.id}")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                invoices_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            session.close()
    
    async def admin_ads(self, user_id: str, query):
        """Admin: Manage ads"""
        session = Session()
        try:
            pending_ads = session.query(Ad).filter_by(
                status='pending'
            ).order_by(Ad.created_at).limit(10).all()
            
            if not pending_ads:
                await query.edit_message_text("📢 هیچ تبلیغ در انتظار تاییدی وجود ندارد.")
                return
            
            ads_text = "📢 *مدیریت تبلیغات*\n\n"
            for ad in pending_ads:
                user = session.query(User).filter_by(id=ad.user_id).first()
                ads_text += f"🆔 {ad.uuid[:8]}\n"
                ads_text += f"👤 کاربر: {user.telegram_id if user else 'نامشخص'}\n"
                ads_text += f"📝 {ad.content[:50]}...\n"
                ads_text += f"💰 {ad.price:,.0f} تومان\n"
                ads_text += "---\n"
            
            keyboard = []
            for ad in pending_ads[:5]:
                keyboard.append([
                    InlineKeyboardButton(f"✅ تایید", callback_data=f"ad_approve_{ad.id}"),
                    InlineKeyboardButton(f"❌ رد", callback_data=f"ad_reject_{ad.id}")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                ads_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            session.close()
    
    async def admin_stats(self, user_id: str, query):
        """Admin: View statistics"""
        await self.stats_command(query.message, None)
    
    async def admin_backup(self, user_id: str, query):
        """Admin: Create backup"""
        await self.backup_command(query.message, None)
    
    async def admin_audit_log(self, user_id: str, query):
        """Admin: View audit log"""
        session = Session()
        try:
            logs = session.query(AuditLog).order_by(
                AuditLog.created_at.desc()
            ).limit(20).all()
            
            if not logs:
                await query.edit_message_text("📋 هیچ لاگی ثبت نشده است.")
                return
            
            log_text = "📋 *لاگ عملیات ادمین*\n\n"
            for log in logs:
                user = session.query(User).filter_by(id=log.user_id).first()
                log_text += f"🆔 {log.uuid[:8]}\n"
                log_text += f"👤 {user.telegram_id if user else 'سیستم'}\n"
                log_text += f"📝 {log.action}: {log.description}\n"
                log_text += f"📅 {log.created_at.strftime('%Y/%m/%d %H:%M')}\n"
                log_text += "---\n"
            
            await query.edit_message_text(
                log_text,
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            session.close()
    
    async def admin_maintenance(self, user_id: str, query):
        """Admin: Toggle maintenance mode"""
        if not await self.is_owner(user_id):
            await query.edit_message_text(I18n.get_text('owner_required'))
            return
        
        session = Session()
        try:
            setting = session.query(SystemSetting).filter_by(key='maintenance_mode').first()
            if not setting:
                setting = SystemSetting(
                    key='maintenance_mode',
                    value='false',
                    category='system',
                    description='Maintenance mode status'
                )
                session.add(setting)
            else:
                setting.value = 'false' if setting.value == 'true' else 'true'
            
            session.commit()
            
            status = "فعال" if setting.value == 'true' else "غیرفعال"
            await query.edit_message_text(
                f"🛠 حالت نگهداری {status} شد.\n"
                f"زمان: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
            )
            
            await self.log_audit(
                user_id,
                'maintenance_toggle',
                f'Maintenance mode set to {status}'
            )
        finally:
            session.close()
    
    async def admin_broadcast(self, user_id: str, query):
        """Admin: Broadcast message"""
        await self.broadcast_command(query.message, None)
    
    async def admin_settings(self, user_id: str, query):
        """Admin: System settings"""
        session = Session()
        try:
            settings = session.query(SystemSetting).all()
            
            if not settings:
                await query.edit_message_text("⚙️ هیچ تنظیماتی یافت نشد.")
                return
            
            settings_text = "⚙️ *تنظیمات سیستم*\n\n"
            for setting in settings:
                settings_text += f"• {setting.key}: {setting.value}\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_refresh_settings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                settings_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            session.close()
    
    async def admin_version(self, user_id: str, query):
        """Admin: Show version info"""
        if not await self.is_owner(user_id):
            await query.edit_message_text(I18n.get_text('owner_required'))
            return
        
        await query.edit_message_text(
            "📌 *اطلاعات سیستم*\n\n"
            "Ghost Assistant\n"
            "نسخه: ۱.۰.۰\n"
            "آخرین بروزرسانی: ۱۴۰۵/۰۴/۲۲\n\n"
            "توسعه‌دهنده: Ghost Team\n"
            "پشتیبانی: @GhostSupport",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ==================== MESSAGE HANDLERS ====================
    
    async def text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user_id = str(update.effective_user.id)
        text = update.message.text
        
        # Rate limiting
        rate_key = f"rate_limit:{user_id}"
        if self.redis.exists(rate_key):
            count = self.redis.incr(rate_key)
            if count > Config.RATE_LIMIT['messages_per_second']:
                await update.message.reply_text(I18n.get_text('rate_limit'))
                return
        else:
            self.redis.set(rate_key, '1', expire=1)
        
        # Check maintenance
        if await self.is_maintenance_mode() and user_id not in Config.OWNER_IDS:
            await update.message.reply_text(I18n.get_text('maintenance'))
            return
        
        # Handle broadcast
        if context.user_data.get('broadcast_step'):
            await self.send_broadcast(update, context)
            return
        
        # Handle AI
        if text.startswith('/ai') or text.startswith('🤖'):
            await self.handle_ai_request(update, context, text)
            return
        
        # Handle receipt
        if context.user_data.get('receipt_step'):
            await self.process_receipt_text(update, context)
            return
        
        # Handle admin actions
        if await self.is_admin(user_id):
            await self.handle_admin_text(update, context, text)
    
    async def photo_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages"""
        user_id = str(update.effective_user.id)
        
        if context.user_data.get('receipt_step'):
            photo = update.message.photo[-1]
            file = await photo.get_file()
            
            os.makedirs('receipts', exist_ok=True)
            file_path = f"receipts/{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            await file.download_to_drive(file_path)
            
            session = Session()
            try:
                user = session.query(User).filter_by(telegram_id=user_id).first()
                if user:
                    invoice = session.query(Invoice).filter_by(
                        user_id=user.id,
                        status='pending'
                    ).order_by(Invoice.created_at.desc()).first()
                    
                    if invoice:
                        invoice.receipt_image = file_path
                        session.commit()
                        
                        await update.message.reply_text(I18n.get_text('receipt_received', user.language))
                        
                        # Notify admins
                        admin_text = (
                            f"📤 *رسید جدید*\n"
                            f"کاربر: {user.telegram_id}\n"
                            f"فاکتور: {invoice.invoice_number}\n"
                            f"مبلغ: {invoice.amount:,.0f} تومان\n"
                            f"برای تایید به پنل ادمین مراجعه کنید."
                        )
                        await self.notify_admins(admin_text)
                    else:
                        await update.message.reply_text(I18n.get_text('receipt_error', user.language))
            finally:
                session.close()
            
            context.user_data['receipt_step'] = False
    
    async def voice_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages"""
        await update.message.reply_text(
            "🎤 صدای شما دریافت شد.\n"
            "در حال پردازش... (این قابلیت به زودی فعال می‌شود)"
        )
    
    async def document_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document uploads"""
        await update.message.reply_text(
            "📄 فایل شما دریافت شد.\n"
            "در حال پردازش... (این قابلیت به زودی فعال می‌شود)"
        )
    
    # ==================== HELPER FUNCTIONS ====================
    
    async def process_receipt_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process receipt text"""
        user_id = str(update.effective_user.id)
        text = update.message.text
        
        # Assume text is sender card number
        if Utils.validate_card_number(text):
            session = Session()
            try:
                user = session.query(User).filter_by(telegram_id=user_id).first()
                if user:
                    invoice = session.query(Invoice).filter_by(
                        user_id=user.id,
                        status='pending'
                    ).order_by(Invoice.created_at.desc()).first()
                    
                    if invoice:
                        invoice.sender_card = text
                        session.commit()
                        
                        await update.message.reply_text(
                            "✅ شماره کارت مبدا ثبت شد.\n"
                            "پس از تایید ادمین، عملیات تکمیل می‌شود."
                        )
                        
                        context.user_data['receipt_step'] = False
                    else:
                        await update.message.reply_text("❌ فاکتور در انتظار پرداختی یافت نشد.")
            finally:
                session.close()
        else:
            await update.message.reply_text(
                "❌ شماره کارت معتبر نیست.\n"
                "لطفاً یک شماره کارت ۱۶ رقمی وارد کنید."
            )
    
    async def handle_admin_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Handle admin text messages"""
        # This can be extended for admin settings changes
        pass
    
    async def handle_ai_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Handle AI requests"""
        user_id = str(update.effective_user.id)
        
        # Remove command prefix
        if text.startswith('/ai'):
            text = text[3:].strip()
        elif text.startswith('🤖'):
            text = text[1:].strip()
        
        if not text:
            await update.message.reply_text(
                "🤖 لطفاً سوال خود را بپرسید.\n"
                "مثال: /ai بهترین ربات تلگرام چیست؟"
            )
            return
        
        # For now, provide a simple response
        response = (
            "🤖 *پاسخ هوش مصنوعی*\n\n"
            f"سوال شما: {text}\n\n"
            "این یک پاسخ آزمایشی است. برای استفاده از هوش مصنوعی واقعی، "
            "لطفاً کلید API را در تنظیمات پیکربندی کنید.\n\n"
            "🔜 به زودی با هوش مصنوعی پیشرفته!"
        )
        
        await update.message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def send_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send broadcast message to all users"""
        user_id = str(update.effective_user.id)
        content = update.message.text
        
        if not await self.is_admin(user_id):
            await update.message.reply_text(I18n.get_text('admin_required'))
            context.user_data['broadcast_step'] = False
            return
        
        session = Session()
        try:
            broadcast = Broadcast(
                uuid=Utils.generate_uuid(),
                content=content,
                target_users='all',
                status='pending',
                created_by=session.query(User).filter_by(telegram_id=user_id).first().id,
                created_at=datetime.now()
            )
            session.add(broadcast)
            session.commit()
            
            users = session.query(User).all()
            total = len(users)
            sent = 0
            
            broadcast.total_count = total
            
            for user in users:
                try:
                    await self.application.bot.send_message(
                        chat_id=user.telegram_id,
                        text=content
                    )
                    sent += 1
                    broadcast.sent_count = sent
                    session.commit()
                except Exception as e:
                    logger.error(f"Error sending to {user.telegram_id}: {e}")
            
            broadcast.status = 'completed'
            broadcast.sent_at = datetime.now()
            session.commit()
            
            context.user_data['broadcast_step'] = False
            
            await update.message.reply_text(
                I18n.get_text('broadcast_sent', 'fa',
                    total=total,
                    sent=sent
                )
            )
            
            await self.log_audit(
                user_id,
                'broadcast',
                f'Sent broadcast to {sent} users',
                {'total': total, 'sent': sent}
            )
        except Exception as e:
            session.rollback()
            await update.message.reply_text(f"❌ خطا در ارسال broadcast: {str(e)}")
        finally:
            session.close()
    
    async def notify_admins(self, message: str):
        """Notify all admins"""
        for admin_id in Config.ADMIN_IDS + Config.OWNER_IDS:
            try:
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error notifying admin {admin_id}: {e}")
    
    # ==================== SCHEDULED JOBS ====================
    
    async def daily_backup(self):
        """Daily backup job"""
        try:
            backup_file = f"backup_{datetime.now().strftime('%Y%m%d')}.db"
            shutil.copy2("ghost_bot.db", backup_file)
            
            backups = sorted([f for f in os.listdir() if f.startswith('backup_') and f.endswith('.db')])
            if len(backups) > 7:
                for f in backups[:-7]:
                    os.remove(f)
            
            logger.info(f"Daily backup created: {backup_file}")
        except Exception as e:
            logger.error(f"Error creating daily backup: {e}")
    
    async def cleanup_expired_premium(self):
        """Cleanup expired premium subscriptions"""
        session = Session()
        try:
            expired_users = session.query(User).filter(
                User.is_premium == True,
                User.premium_expire < datetime.now()
            ).all()
            
            for user in expired_users:
                user.is_premium = False
                user.premium_expire = None
                
                audit = AuditLog(
                    user_id=user.id,
                    action='premium_expired',
                    description='Premium subscription expired',
                    details={'expired_at': datetime.now().isoformat()}
                )
                session.add(audit)
            
            session.commit()
            logger.info(f"Cleaned up {len(expired_users)} expired premium users")
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning expired premium: {e}")
        finally:
            session.close()
    
    async def update_ad_stats(self):
        """Update ad statistics"""
        session = Session()
        try:
            active_ads = session.query(Ad).filter_by(status='active').all()
            for ad in active_ads:
                ad.views += 1
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating ad stats: {e}")
        finally:
            session.close()
    
    # ==================== ERROR HANDLER ====================
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Global error handler"""
        logger.error(f"Update {update} caused error {context.error}")
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ خطایی رخ داد. لطفاً بعداً دوباره تلاش کنید."
                )
        except:
            pass
    
    # ==================== RUN BOT ====================
    
    def run(self):
        """Run the bot"""
        logger.info("Starting Ghost Assistant Bot...")
        
        os.makedirs('receipts', exist_ok=True)
        os.makedirs('voice', exist_ok=True)
        os.makedirs('backups', exist_ok=True)
        
        self.scheduler.start()
        
        logger.info("Bot is running! Press Ctrl+C to stop.")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

# ==================== MAIN ====================

def main():
    """Main entry point"""
    try:
        bot = GhostBot(Config.TOKEN)
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == '__main__':
    main()
