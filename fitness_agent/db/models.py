from datetime import date, datetime, time, timezone
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Date, Time
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from fitness_agent.db.base import Base

def enum_values(enum_class):
    return [member.value for member in enum_class]

class MemberStatus(StrEnum):
    ACTIVE = "active"
    FROZEN = "frozen"
    PAST_DUE = "past_due"

class Member(Base):
    __tablename__ = "members"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    plan: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[MemberStatus] = mapped_column(
        SqlEnum(
            MemberStatus,
            values_callable=enum_values,
            name="member_status"
        ),
        nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    home_location: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

class Instructor(Base):
    __tablename__ = "instructors"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    bio: Mapped[str] = mapped_column(String, nullable=False)

class ClassType(Base):
    __tablename__ = "class_types"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    intensity: Mapped[str] = mapped_column(String, nullable=False)
    plan_required: Mapped[str] = mapped_column(String, nullable=False)

class ClassScheduleStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    RETIRED = "retired"

class ClassSchedule(Base):
    __tablename__ = "class_schedules"

    id: Mapped[str] = mapped_column(String, primary_key=True)

    class_type_id: Mapped[str] = mapped_column(
        ForeignKey("class_types.id"),
        nullable=False,
    )

    instructor_id: Mapped[str] = mapped_column(
        ForeignKey("instructors.id"),
        nullable=False,
    )

    location: Mapped[str] = mapped_column(String, nullable=False)

    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    status: Mapped[ClassScheduleStatus] = mapped_column(
        SqlEnum(
            ClassScheduleStatus,
            values_callable=enum_values,
            name="class_schedule_status"),
        nullable=False,
    )

class ClassSessionStatus(StrEnum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class ClassSession(Base):
    __tablename__ = "class_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)

    class_type_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("class_types.id"),
        nullable=False
    )

    instructor_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("instructors.id"),
        nullable=False
    )

    location: Mapped[str] = mapped_column(String, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone = True), nullable=False)

    capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[ClassSessionStatus] = mapped_column(
        SqlEnum(
            ClassSessionStatus,
            values_callable=enum_values,
            name="class_session_status"),
        nullable=False
    )

class BookingStatus(StrEnum):
    BOOKED = "booked"
    CANCELLED = "cancelled"
    WAITLISTED = "waitlisted"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String, primary_key=True)

    member_id: Mapped[str] = mapped_column(
        ForeignKey("members.id"),
        nullable=False,
    )

    class_session_id: Mapped[str] = mapped_column(
        ForeignKey("class_sessions.id"),
        nullable=False,
    )

    status: Mapped[BookingStatus] = mapped_column(
        SqlEnum(
            BookingStatus,
            values_callable=enum_values,
            name="booking_status"),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )