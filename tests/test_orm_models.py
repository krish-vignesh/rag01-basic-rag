import asyncio
import sys
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.enum import CompanyRole, DepartmentType, InvitationStatus
from src.models.orm.company import Company
from src.models.orm.company_membership import CompanyMembership
from src.models.orm.department import Department
from src.models.orm.invitation import Invitation
from src.models.orm.membership_audit_event import MembershipAuditEvent
from src.models.orm.platform_admin import PlatformAdmin
from src.models.orm.platform_audit_event import PlatformAuditEvent
from src.models.orm.user import User

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


async def _create_company(session: AsyncSession) -> Company:
    company = Company(company_name=_unique("company"))
    session.add(company)
    await session.flush()
    return company


async def _create_user(
    session: AsyncSession,
    *,
    email: str | None = None,
) -> User:
    user = User(
        keycloak_sub=_unique("subject"),
        email=email or f"{_unique('user')}@example.test",
    )
    session.add(user)
    await session.flush()
    return user


async def _create_department(
    session: AsyncSession,
    company_id: UUID,
    *,
    name: str | None = None,
) -> Department:
    department = Department(
        company_id=company_id,
        department_name=name or _unique("department"),
        department_type=DepartmentType.GENERAL,
    )
    session.add(department)
    await session.flush()
    return department


async def _create_membership(
    session: AsyncSession,
    company_id: UUID,
    user_id: UUID,
    *,
    department_id: UUID | None = None,
    role: CompanyRole = CompanyRole.COMPANY_OWNER,
) -> CompanyMembership:
    membership = CompanyMembership(
        company_id=company_id,
        user_id=user_id,
        department_id=department_id,
        role_code=role,
    )
    session.add(membership)
    await session.flush()
    return membership


async def _assert_integrity_error(
    session: AsyncSession,
    record: object,
) -> None:
    session.add(record)
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()
    await session.execute(select(1))


@pytest.mark.asyncio
async def test_user_persists_generated_fields_and_allows_duplicate_email(
    orm_test_session: AsyncSession,
) -> None:
    email = f"{_unique('shared')}@example.test"
    first = await _create_user(orm_test_session, email=email)
    second = await _create_user(orm_test_session, email=email)

    assert isinstance(first.user_id, UUID)
    assert isinstance(second.user_id, UUID)
    assert first.user_id != second.user_id
    assert first.display_name is None
    assert first.created_at is not None
    assert first.updated_at is not None

    persisted = await orm_test_session.scalar(
        select(User).where(User.user_id == first.user_id)
    )
    assert persisted is not None
    assert persisted.email == email


@pytest.mark.asyncio
async def test_user_rejects_duplicate_keycloak_subject(
    orm_test_session: AsyncSession,
) -> None:
    subject = _unique("subject")
    orm_test_session.add(User(keycloak_sub=subject, email="one@example.test"))
    await orm_test_session.flush()

    await _assert_integrity_error(
        orm_test_session,
        User(keycloak_sub=subject, email="two@example.test"),
    )


@pytest.mark.asyncio
async def test_department_persists_defaults_and_allows_same_name_across_companies(
    orm_test_session: AsyncSession,
) -> None:
    first_company = await _create_company(orm_test_session)
    second_company = await _create_company(orm_test_session)
    name = _unique("shared-department")

    first = Department(
        company_id=first_company.company_id,
        department_name=name,
        department_type=DepartmentType.HR,
    )
    second = Department(
        company_id=second_company.company_id,
        department_name=name,
        department_type=DepartmentType.IT_SUPPORT,
    )
    orm_test_session.add_all([first, second])
    await orm_test_session.flush()

    assert isinstance(first.department_id, UUID)
    assert first.status == "ACTIVE"
    assert first.created_at is not None
    assert first.updated_at is not None


@pytest.mark.asyncio
async def test_department_rejects_duplicate_name_within_company(
    orm_test_session: AsyncSession,
) -> None:
    company = await _create_company(orm_test_session)
    name = _unique("duplicate-department")
    await _create_department(orm_test_session, company.company_id, name=name)

    await _assert_integrity_error(
        orm_test_session,
        Department(
            company_id=company.company_id,
            department_name=name,
            department_type=DepartmentType.GENERAL,
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("department_type", "status"),
    [
        ("INVALID", "ACTIVE"),
        (DepartmentType.GENERAL, "INVALID"),
    ],
)
async def test_department_rejects_invalid_type_or_status(
    orm_test_session: AsyncSession,
    department_type: str,
    status: str,
) -> None:
    company = await _create_company(orm_test_session)
    await _assert_integrity_error(
        orm_test_session,
        Department(
            company_id=company.company_id,
            department_name=_unique("invalid-department"),
            department_type=department_type,
            status=status,
        ),
    )


@pytest.mark.asyncio
async def test_company_owner_membership_allows_no_department(
    orm_test_session: AsyncSession,
) -> None:
    company = await _create_company(orm_test_session)
    user = await _create_user(orm_test_session)

    membership = await _create_membership(
        orm_test_session,
        company.company_id,
        user.user_id,
    )

    assert isinstance(membership.membership_id, UUID)
    assert membership.department_id is None
    assert membership.status == "ACTIVE"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        CompanyRole.DEPARTMENT_MANAGER,
        CompanyRole.OPERATOR,
        CompanyRole.EMPLOYEE,
    ],
)
async def test_departmental_membership_requires_and_accepts_department(
    orm_test_session: AsyncSession,
    role: CompanyRole,
) -> None:
    company = await _create_company(orm_test_session)
    user = await _create_user(orm_test_session)
    department = await _create_department(
        orm_test_session,
        company.company_id,
    )

    membership = await _create_membership(
        orm_test_session,
        company.company_id,
        user.user_id,
        department_id=department.department_id,
        role=role,
    )

    assert membership.role_code == role
    assert membership.department_id == department.department_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "department_id"),
    [
        ("INVALID", None),
        (CompanyRole.COMPANY_OWNER, uuid4()),
        (CompanyRole.EMPLOYEE, None),
    ],
)
async def test_membership_rejects_invalid_role_department_combination(
    orm_test_session: AsyncSession,
    role: str,
    department_id: UUID | None,
) -> None:
    company = await _create_company(orm_test_session)
    user = await _create_user(orm_test_session)

    await _assert_integrity_error(
        orm_test_session,
        CompanyMembership(
            company_id=company.company_id,
            user_id=user.user_id,
            department_id=department_id,
            role_code=role,
        ),
    )


@pytest.mark.asyncio
async def test_membership_rejects_duplicate_user_membership(
    orm_test_session: AsyncSession,
) -> None:
    first_company = await _create_company(orm_test_session)
    second_company = await _create_company(orm_test_session)
    user = await _create_user(orm_test_session)
    await _create_membership(
        orm_test_session,
        first_company.company_id,
        user.user_id,
    )

    await _assert_integrity_error(
        orm_test_session,
        CompanyMembership(
            company_id=second_company.company_id,
            user_id=user.user_id,
            role_code=CompanyRole.COMPANY_OWNER,
        ),
    )


@pytest.mark.asyncio
async def test_membership_rejects_department_from_another_company(
    orm_test_session: AsyncSession,
) -> None:
    first_company = await _create_company(orm_test_session)
    second_company = await _create_company(orm_test_session)
    user = await _create_user(orm_test_session)
    department = await _create_department(
        orm_test_session,
        first_company.company_id,
    )

    await _assert_integrity_error(
        orm_test_session,
        CompanyMembership(
            company_id=second_company.company_id,
            user_id=user.user_id,
            department_id=department.department_id,
            role_code=CompanyRole.EMPLOYEE,
        ),
    )


@pytest.mark.asyncio
async def test_invitation_persists_pending_default_and_owner_without_department(
    orm_test_session: AsyncSession,
) -> None:
    company = await _create_company(orm_test_session)
    user = await _create_user(orm_test_session)
    inviter = await _create_membership(
        orm_test_session,
        company.company_id,
        user.user_id,
    )
    invitation = Invitation(
        company_id=company.company_id,
        invited_by_membership_id=inviter.membership_id,
        invited_email=f"{_unique('invite')}@example.test",
        role_code=CompanyRole.COMPANY_OWNER,
        token_hash=_unique("synthetic-token-hash"),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    orm_test_session.add(invitation)
    await orm_test_session.flush()

    assert isinstance(invitation.invitation_id, UUID)
    assert invitation.status == InvitationStatus.PENDING
    assert invitation.department_id is None
    assert invitation.created_at is not None


@pytest.mark.asyncio
async def test_departmental_invitation_accepts_department_and_status(
    orm_test_session: AsyncSession,
) -> None:
    company = await _create_company(orm_test_session)
    user = await _create_user(orm_test_session)
    inviter = await _create_membership(
        orm_test_session,
        company.company_id,
        user.user_id,
    )
    department = await _create_department(
        orm_test_session,
        company.company_id,
    )
    invitation = Invitation(
        company_id=company.company_id,
        department_id=department.department_id,
        invited_by_membership_id=inviter.membership_id,
        invited_email=f"{_unique('invite')}@example.test",
        role_code=CompanyRole.EMPLOYEE,
        token_hash=_unique("synthetic-token-hash"),
        status=InvitationStatus.ACCEPTED,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    orm_test_session.add(invitation)
    await orm_test_session.flush()

    assert invitation.department_id == department.department_id
    assert invitation.status == InvitationStatus.ACCEPTED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "status"),
    [
        ("INVALID", InvitationStatus.PENDING),
        (CompanyRole.COMPANY_OWNER, "INVALID"),
    ],
)
async def test_invitation_rejects_invalid_role_or_status(
    orm_test_session: AsyncSession,
    role: str,
    status: str,
) -> None:
    company = await _create_company(orm_test_session)
    user = await _create_user(orm_test_session)
    inviter = await _create_membership(
        orm_test_session,
        company.company_id,
        user.user_id,
    )

    await _assert_integrity_error(
        orm_test_session,
        Invitation(
            company_id=company.company_id,
            invited_by_membership_id=inviter.membership_id,
            invited_email=f"{_unique('invite')}@example.test",
            role_code=role,
            token_hash=_unique("synthetic-token-hash"),
            status=status,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        ),
    )


@pytest.mark.asyncio
async def test_departmental_invitation_requires_department(
    orm_test_session: AsyncSession,
) -> None:
    company = await _create_company(orm_test_session)
    user = await _create_user(orm_test_session)
    inviter = await _create_membership(
        orm_test_session,
        company.company_id,
        user.user_id,
    )

    await _assert_integrity_error(
        orm_test_session,
        Invitation(
            company_id=company.company_id,
            invited_by_membership_id=inviter.membership_id,
            invited_email=f"{_unique('invite')}@example.test",
            role_code=CompanyRole.EMPLOYEE,
            token_hash=_unique("synthetic-token-hash"),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        ),
    )


@pytest.mark.asyncio
async def test_invitation_rejects_department_from_another_company(
    orm_test_session: AsyncSession,
) -> None:
    first_company = await _create_company(orm_test_session)
    second_company = await _create_company(orm_test_session)
    user = await _create_user(orm_test_session)
    inviter = await _create_membership(
        orm_test_session,
        second_company.company_id,
        user.user_id,
    )
    department = await _create_department(
        orm_test_session,
        first_company.company_id,
    )

    await _assert_integrity_error(
        orm_test_session,
        Invitation(
            company_id=second_company.company_id,
            department_id=department.department_id,
            invited_by_membership_id=inviter.membership_id,
            invited_email=f"{_unique('invite')}@example.test",
            role_code=CompanyRole.EMPLOYEE,
            token_hash=_unique("synthetic-token-hash"),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        ),
    )


@pytest.mark.asyncio
async def test_invitation_rejects_inviter_membership_from_another_company(
    orm_test_session: AsyncSession,
) -> None:
    inviter_company = await _create_company(orm_test_session)
    invitation_company = await _create_company(orm_test_session)
    user = await _create_user(orm_test_session)
    inviter = await _create_membership(
        orm_test_session,
        inviter_company.company_id,
        user.user_id,
    )

    await _assert_integrity_error(
        orm_test_session,
        Invitation(
            company_id=invitation_company.company_id,
            invited_by_membership_id=inviter.membership_id,
            invited_email=f"{_unique('invite')}@example.test",
            role_code=CompanyRole.COMPANY_OWNER,
            token_hash=_unique("synthetic-token-hash"),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        ),
    )


@pytest.mark.asyncio
async def test_invitation_rejects_duplicate_token_hash(
    orm_test_session: AsyncSession,
) -> None:
    company = await _create_company(orm_test_session)
    user = await _create_user(orm_test_session)
    inviter = await _create_membership(
        orm_test_session,
        company.company_id,
        user.user_id,
    )
    token_hash = _unique("synthetic-token-hash")
    common = {
        "company_id": company.company_id,
        "invited_by_membership_id": inviter.membership_id,
        "invited_email": f"{_unique('invite')}@example.test",
        "role_code": CompanyRole.COMPANY_OWNER,
        "expires_at": datetime.now(UTC) + timedelta(days=1),
    }
    orm_test_session.add(
        Invitation(token_hash=token_hash, **common)
    )
    await orm_test_session.flush()

    await _assert_integrity_error(
        orm_test_session,
        Invitation(token_hash=token_hash, **common),
    )


@pytest.mark.asyncio
async def test_membership_audit_event_persists_json_and_optional_actor(
    orm_test_session: AsyncSession,
) -> None:
    company = await _create_company(orm_test_session)
    member_user = await _create_user(orm_test_session)
    actor_user = await _create_user(orm_test_session)
    membership = await _create_membership(
        orm_test_session,
        company.company_id,
        member_user.user_id,
    )
    actor = await _create_membership(
        orm_test_session,
        company.company_id,
        actor_user.user_id,
    )
    values = {"role_code": "EMPLOYEE"}
    event = MembershipAuditEvent(
        membership_id=membership.membership_id,
        actor_membership_id=actor.membership_id,
        event_type="membership.updated",
        old_values={"role_code": "OPERATOR"},
        new_values=values,
    )
    orm_test_session.add(event)
    await orm_test_session.flush()
    await orm_test_session.refresh(event)

    assert isinstance(event.event_id, UUID)
    assert event.created_at is not None
    assert event.new_values == values
    assert event.actor_membership_id == actor.membership_id

    actorless_event = MembershipAuditEvent(
        membership_id=membership.membership_id,
        actor_membership_id=None,
        event_type="membership.system_update",
    )
    orm_test_session.add(actorless_event)
    await orm_test_session.flush()
    assert actorless_event.actor_membership_id is None


@pytest.mark.asyncio
async def test_membership_audit_event_rejects_unknown_membership(
    orm_test_session: AsyncSession,
) -> None:
    await _assert_integrity_error(
        orm_test_session,
        MembershipAuditEvent(
            membership_id=uuid4(),
            event_type="membership.updated",
        ),
    )


@pytest.mark.asyncio
async def test_platform_admin_uses_singleton_and_active_defaults(
    orm_test_session: AsyncSession,
) -> None:
    user = await _create_user(orm_test_session)
    admin = PlatformAdmin(user_id=user.user_id)
    orm_test_session.add(admin)
    await orm_test_session.flush()

    assert admin.platform_admin_id == 1
    assert admin.status == "ACTIVE"
    assert admin.created_at is not None
    assert admin.updated_at is not None


@pytest.mark.asyncio
async def test_platform_admin_rejects_non_singleton_id(
    orm_test_session: AsyncSession,
) -> None:
    user = await _create_user(orm_test_session)
    await _assert_integrity_error(
        orm_test_session,
        PlatformAdmin(platform_admin_id=2, user_id=user.user_id),
    )


@pytest.mark.asyncio
async def test_platform_admin_rejects_invalid_status(
    orm_test_session: AsyncSession,
) -> None:
    user = await _create_user(orm_test_session)
    await _assert_integrity_error(
        orm_test_session,
        PlatformAdmin(user_id=user.user_id, status="INVALID"),
    )


@pytest.mark.asyncio
async def test_platform_audit_event_persists_details(
    orm_test_session: AsyncSession,
) -> None:
    user = await _create_user(orm_test_session)
    details = {"action": "policy.changed", "enabled": True}
    event = PlatformAuditEvent(
        actor_user_id=user.user_id,
        event_type="platform.policy_changed",
        details=details,
    )
    orm_test_session.add(event)
    await orm_test_session.flush()
    await orm_test_session.refresh(event)

    assert isinstance(event.event_id, UUID)
    assert event.created_at is not None
    assert event.details == details


@pytest.mark.asyncio
async def test_platform_audit_event_rejects_unknown_actor(
    orm_test_session: AsyncSession,
) -> None:
    await _assert_integrity_error(
        orm_test_session,
        PlatformAuditEvent(
            actor_user_id=uuid4(),
            event_type="platform.policy_changed",
        ),
    )
