import pytest
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from hypothesis import given, settings, strategies as st, assume

from app import create_app
from app.extensions import db
from app.models import Exercise, Invoice, Member, Package, User, WorkoutDetail, WorkoutPlan
from app.utils import format_vnd

settings.register_profile("ci", max_examples=100)
settings.load_profile("ci")

class TestVNDFormatting:
    @given(st.floats(min_value=0, max_value=1e12, allow_nan=False, allow_infinity=False))
    def test_format_vnd_contains_vnd_suffix(self, amount: float) -> None:
        result = format_vnd(amount)
        assert "VND" in result, f"Result '{result}' does not contain 'VND'"

    @given(st.integers(min_value=0, max_value=10**12))
    def test_format_vnd_contains_formatted_number(self, amount: int) -> None:
        result = format_vnd(amount)
        number_part = result.replace(" VND", "").replace(",", "")
        assert number_part == str(amount), f"Number part '{number_part}' does not match '{amount}'"

    @given(st.integers(min_value=1000, max_value=10**12))
    def test_format_vnd_has_thousand_separators(self, amount: int) -> None:
        result = format_vnd(amount)
        number_part = result.replace(" VND", "")
        assert "," in number_part, f"Result '{result}' should have thousand separators for amount {amount}"

class TestConfig:
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    LOGIN_DISABLED = True

valid_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "Zs")),
    min_size=1,
    max_size=100
).filter(lambda x: x.strip())

valid_email_strategy = st.emails()

valid_phone_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Nd",)),
    min_size=10,
    max_size=15
).filter(lambda x: len(x) >= 10)

valid_gender_strategy = st.sampled_from(["Male", "Female", "Other"])

valid_dob_strategy = st.dates(
    min_value=date(1950, 1, 1),
    max_value=date(2005, 12, 31)
)

valid_duration_strategy = st.integers(min_value=1, max_value=24)

valid_price_strategy = st.integers(min_value=100000, max_value=10000000)

class TestRegistrationCreatesInvoice:
    @given(
        full_name=valid_name_strategy,
        email=valid_email_strategy,
        phone=valid_phone_strategy,
        gender=valid_gender_strategy,
        dob=valid_dob_strategy,
        duration_months=valid_duration_strategy,
        price=valid_price_strategy,
    )
    @settings(max_examples=100)
    def test_registration_creates_exactly_one_invoice(
        self,
        full_name: str,
        email: str,
        phone: str,
        gender: str,
        dob: date,
        duration_months: int,
        price: int,
    ) -> None:
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                package = Package(
                    name=f"Test Package {duration_months}m",
                    duration_months=duration_months,
                    price=price,
                    description="Test package"
                )
                db.session.add(package)
                db.session.commit()
                package_id = package.id
                
                registration_date = datetime.utcnow()
                active_until = (registration_date + relativedelta(months=duration_months)).date()
                
                member = Member(
                    full_name=full_name.strip(),
                    gender=gender,
                    dob=dob,
                    phone=phone,
                    email=email,
                    registration_date=registration_date,
                    active_until=active_until,
                )
                db.session.add(member)
                db.session.flush()
                
                invoice = Invoice(
                    member_id=member.id,
                    package_id=package_id,
                    amount=price,
                )
                db.session.add(invoice)
                db.session.commit()
                
                member_invoices = Invoice.query.filter_by(member_id=member.id).all()
                assert len(member_invoices) == 1, f"Expected 1 invoice, got {len(member_invoices)}"
                
                created_invoice = member_invoices[0]
                assert created_invoice.package_id == package_id, "Invoice linked to wrong package"
                assert created_invoice.amount == price, f"Invoice amount {created_invoice.amount} != package price {price}"
                
            finally:
                db.session.remove()
                db.drop_all()

class TestRegistrationSetsActiveUntil:
    @given(
        full_name=valid_name_strategy,
        email=valid_email_strategy,
        phone=valid_phone_strategy,
        gender=valid_gender_strategy,
        dob=valid_dob_strategy,
        duration_months=valid_duration_strategy,
    )
    @settings(max_examples=100)
    def test_active_until_is_n_months_from_registration(
        self,
        full_name: str,
        email: str,
        phone: str,
        gender: str,
        dob: date,
        duration_months: int,
    ) -> None:
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                package = Package(
                    name=f"Test Package {duration_months}m",
                    duration_months=duration_months,
                    price=500000,
                    description="Test package"
                )
                db.session.add(package)
                db.session.commit()
                
                registration_date = datetime.utcnow()
                expected_active_until = (registration_date + relativedelta(months=duration_months)).date()
                
                member = Member(
                    full_name=full_name.strip(),
                    gender=gender,
                    dob=dob,
                    phone=phone,
                    email=email,
                    registration_date=registration_date,
                    active_until=expected_active_until,
                )
                db.session.add(member)
                db.session.commit()
                
                saved_member = Member.query.filter_by(email=email).first()
                assert saved_member is not None, "Member was not saved"
                assert saved_member.active_until == expected_active_until, (
                    f"active_until {saved_member.active_until} != expected {expected_active_until}"
                )
                
                calculated_active_until = (
                    saved_member.registration_date + relativedelta(months=duration_months)
                ).date()
                assert saved_member.active_until == calculated_active_until, (
                    f"active_until {saved_member.active_until} != calculated {calculated_active_until}"
                )
                
            finally:
                db.session.remove()
                db.drop_all()

class TestInvoiceListOrdering:
    @given(
        num_invoices=st.integers(min_value=2, max_value=10),
    )
    @settings(max_examples=100)
    def test_invoices_ordered_by_created_at_descending(
        self,
        num_invoices: int,
    ) -> None:
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                package = Package(
                    name="Test Package",
                    duration_months=1,
                    price=500000,
                    description="Test package"
                )
                db.session.add(package)
                db.session.commit()
                
                member = Member(
                    full_name="Test Member",
                    gender="Male",
                    dob=date(1990, 1, 1),
                    phone="0123456789",
                    email="test@example.com",
                    registration_date=datetime.utcnow(),
                    active_until=date.today() + timedelta(days=30),
                )
                db.session.add(member)
                db.session.commit()
                
                base_time = datetime.utcnow()
                for i in range(num_invoices):
                    invoice = Invoice(
                        member_id=member.id,
                        package_id=package.id,
                        amount=500000,
                        created_at=base_time - timedelta(hours=i * 2),  # Spread out in time
                    )
                    db.session.add(invoice)
                db.session.commit()
                
                invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
                
                for i in range(len(invoices) - 1):
                    assert invoices[i].created_at >= invoices[i + 1].created_at, (
                        f"Invoice {i} created_at {invoices[i].created_at} should be >= "
                        f"Invoice {i+1} created_at {invoices[i + 1].created_at}"
                    )
                
            finally:
                db.session.remove()
                db.drop_all()

class TestMemberFilterCorrectness:
    @given(
        num_members=st.integers(min_value=2, max_value=5),
        invoices_per_member=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=100)
    def test_member_filter_returns_only_matching_invoices(
        self,
        num_members: int,
        invoices_per_member: int,
    ) -> None:
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                package = Package(
                    name="Test Package",
                    duration_months=1,
                    price=500000,
                    description="Test package"
                )
                db.session.add(package)
                db.session.commit()
                
                member_ids = []
                for m in range(num_members):
                    member = Member(
                        full_name=f"Test Member {m}",
                        gender="Male",
                        dob=date(1990, 1, 1),
                        phone=f"012345678{m}",
                        email=f"test{m}@example.com",
                        registration_date=datetime.utcnow(),
                        active_until=date.today() + timedelta(days=30),
                    )
                    db.session.add(member)
                    db.session.flush()
                    member_ids.append(member.id)
                    
                    for i in range(invoices_per_member):
                        invoice = Invoice(
                            member_id=member.id,
                            package_id=package.id,
                            amount=500000,
                        )
                        db.session.add(invoice)
                db.session.commit()
                
                for target_member_id in member_ids:
                    filtered_invoices = Invoice.query.filter(
                        Invoice.member_id == target_member_id
                    ).all()
                    
                    for invoice in filtered_invoices:
                        assert invoice.member_id == target_member_id, (
                            f"Invoice member_id {invoice.member_id} != filter value {target_member_id}"
                        )
                    
                    assert len(filtered_invoices) == invoices_per_member, (
                        f"Expected {invoices_per_member} invoices, got {len(filtered_invoices)}"
                    )
                
            finally:
                db.session.remove()
                db.drop_all()

class TestDateRangeFilterCorrectness:
    @given(
        days_spread=st.integers(min_value=5, max_value=30),
        filter_start_offset=st.integers(min_value=1, max_value=10),
        filter_end_offset=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100)
    def test_date_range_filter_returns_only_invoices_within_range(
        self,
        days_spread: int,
        filter_start_offset: int,
        filter_end_offset: int,
    ) -> None:
        assume(filter_start_offset < days_spread - filter_end_offset)
        
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                package = Package(
                    name="Test Package",
                    duration_months=1,
                    price=500000,
                    description="Test package"
                )
                db.session.add(package)
                db.session.commit()
                
                member = Member(
                    full_name="Test Member",
                    gender="Male",
                    dob=date(1990, 1, 1),
                    phone="0123456789",
                    email="test@example.com",
                    registration_date=datetime.utcnow(),
                    active_until=date.today() + timedelta(days=30),
                )
                db.session.add(member)
                db.session.commit()
                
                base_time = datetime.utcnow()
                for i in range(days_spread):
                    invoice = Invoice(
                        member_id=member.id,
                        package_id=package.id,
                        amount=500000,
                        created_at=base_time - timedelta(days=i),
                    )
                    db.session.add(invoice)
                db.session.commit()
                
                start_date = base_time - timedelta(days=days_spread - filter_start_offset)
                end_date = base_time - timedelta(days=filter_end_offset)
                end_date_inclusive = end_date.replace(hour=23, minute=59, second=59)
                
                filtered_invoices = Invoice.query.filter(
                    Invoice.created_at >= start_date,
                    Invoice.created_at <= end_date_inclusive,
                ).all()
                
                for invoice in filtered_invoices:
                    assert invoice.created_at >= start_date, (
                        f"Invoice created_at {invoice.created_at} < start_date {start_date}"
                    )
                    assert invoice.created_at <= end_date_inclusive, (
                        f"Invoice created_at {invoice.created_at} > end_date {end_date_inclusive}"
                    )
                
            finally:
                db.session.remove()
                db.drop_all()

class TestActiveMemberCountAccuracy:
    @given(
        num_active=st.integers(min_value=0, max_value=10),
        num_inactive=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100)
    def test_active_member_count_equals_members_with_valid_active_until(
        self,
        num_active: int,
        num_inactive: int,
    ) -> None:
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                today = date.today()
                
                for i in range(num_active):
                    days_ahead = i + 1  # 1 to num_active days in the future
                    member = Member(
                        full_name=f"Active Member {i}",
                        gender="Male",
                        dob=date(1990, 1, 1),
                        phone=f"012345678{i}",
                        email=f"active{i}@example.com",
                        registration_date=datetime.utcnow(),
                        active_until=today + timedelta(days=days_ahead),
                    )
                    db.session.add(member)
                
                for i in range(num_inactive):
                    days_ago = i + 1  # 1 to num_inactive days in the past
                    member = Member(
                        full_name=f"Inactive Member {i}",
                        gender="Female",
                        dob=date(1990, 1, 1),
                        phone=f"098765432{i}",
                        email=f"inactive{i}@example.com",
                        registration_date=datetime.utcnow(),
                        active_until=today - timedelta(days=days_ago),
                    )
                    db.session.add(member)
                
                db.session.commit()
                
                active_count = Member.query.filter(Member.active_until >= today).count()
                
                assert active_count == num_active, (
                    f"Active member count {active_count} != expected {num_active}"
                )
                
            finally:
                db.session.remove()
                db.drop_all()

    @given(
        num_members=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100)
    def test_members_with_active_until_today_are_counted_as_active(
        self,
        num_members: int,
    ) -> None:
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                today = date.today()
                
                for i in range(num_members):
                    member = Member(
                        full_name=f"Today Member {i}",
                        gender="Male",
                        dob=date(1990, 1, 1),
                        phone=f"012345678{i}",
                        email=f"today{i}@example.com",
                        registration_date=datetime.utcnow(),
                        active_until=today,  # Exactly today
                    )
                    db.session.add(member)
                
                db.session.commit()
                
                active_count = Member.query.filter(Member.active_until >= today).count()
                
                assert active_count == num_members, (
                    f"Members with active_until=today should be active. "
                    f"Got {active_count}, expected {num_members}"
                )
                
            finally:
                db.session.remove()
                db.drop_all()

class TestMembersPerPackageGrouping:
    @given(
        num_members=st.integers(min_value=1, max_value=5),
        num_packages=st.integers(min_value=2, max_value=4),
    )
    @settings(max_examples=100)
    def test_active_members_grouped_by_most_recent_package(
        self,
        num_members: int,
        num_packages: int,
    ) -> None:
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                today = date.today()
                
                packages = []
                for i in range(num_packages):
                    package = Package(
                        name=f"Package {i}",
                        duration_months=i + 1,
                        price=500000 * (i + 1),
                        description=f"Test package {i}"
                    )
                    db.session.add(package)
                    packages.append(package)
                db.session.commit()
                
                expected_counts = {}
                
                for m in range(num_members):
                    member = Member(
                        full_name=f"Test Member {m}",
                        gender="Male",
                        dob=date(1990, 1, 1),
                        phone=f"012345678{m}",
                        email=f"member{m}@example.com",
                        registration_date=datetime.utcnow(),
                        active_until=today + timedelta(days=30),  # Active
                    )
                    db.session.add(member)
                    db.session.flush()
                    
                    base_time = datetime.utcnow()
                    
                    old_invoice = Invoice(
                        member_id=member.id,
                        package_id=packages[0].id,
                        amount=packages[0].price,
                        created_at=base_time - timedelta(days=30),
                    )
                    db.session.add(old_invoice)
                    
                    recent_package_idx = m % num_packages
                    recent_invoice = Invoice(
                        member_id=member.id,
                        package_id=packages[recent_package_idx].id,
                        amount=packages[recent_package_idx].price,
                        created_at=base_time,  # Most recent
                    )
                    db.session.add(recent_invoice)
                    
                    package_name = packages[recent_package_idx].name
                    expected_counts[package_name] = expected_counts.get(package_name, 0) + 1
                
                db.session.commit()
                
                active_members_list = Member.query.filter(Member.active_until >= today).all()
                actual_counts = {}
                
                for member in active_members_list:
                    latest_invoice = (
                        Invoice.query
                        .filter(Invoice.member_id == member.id)
                        .order_by(Invoice.created_at.desc())
                        .first()
                    )
                    if latest_invoice and latest_invoice.package:
                        package_name = latest_invoice.package.name
                        actual_counts[package_name] = actual_counts.get(package_name, 0) + 1
                
                assert actual_counts == expected_counts, (
                    f"Package grouping mismatch. Expected {expected_counts}, got {actual_counts}"
                )
                
            finally:
                db.session.remove()
                db.drop_all()

    @given(
        num_active=st.integers(min_value=1, max_value=5),
        num_inactive=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=100)
    def test_only_active_members_included_in_package_grouping(
        self,
        num_active: int,
        num_inactive: int,
    ) -> None:
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                today = date.today()
                
                package = Package(
                    name="Test Package",
                    duration_months=1,
                    price=500000,
                    description="Test package"
                )
                db.session.add(package)
                db.session.commit()
                
                for i in range(num_active):
                    member = Member(
                        full_name=f"Active Member {i}",
                        gender="Male",
                        dob=date(1990, 1, 1),
                        phone=f"012345678{i}",
                        email=f"active{i}@example.com",
                        registration_date=datetime.utcnow(),
                        active_until=today + timedelta(days=30),
                    )
                    db.session.add(member)
                    db.session.flush()
                    
                    invoice = Invoice(
                        member_id=member.id,
                        package_id=package.id,
                        amount=package.price,
                    )
                    db.session.add(invoice)
                
                for i in range(num_inactive):
                    member = Member(
                        full_name=f"Inactive Member {i}",
                        gender="Female",
                        dob=date(1990, 1, 1),
                        phone=f"098765432{i}",
                        email=f"inactive{i}@example.com",
                        registration_date=datetime.utcnow(),
                        active_until=today - timedelta(days=1),  # Inactive
                    )
                    db.session.add(member)
                    db.session.flush()
                    
                    invoice = Invoice(
                        member_id=member.id,
                        package_id=package.id,
                        amount=package.price,
                    )
                    db.session.add(invoice)
                
                db.session.commit()
                
                active_members_list = Member.query.filter(Member.active_until >= today).all()
                total_in_grouping = 0
                
                for member in active_members_list:
                    latest_invoice = (
                        Invoice.query
                        .filter(Invoice.member_id == member.id)
                        .order_by(Invoice.created_at.desc())
                        .first()
                    )
                    if latest_invoice and latest_invoice.package:
                        total_in_grouping += 1
                
                assert total_in_grouping == num_active, (
                    f"Expected {num_active} members in grouping, got {total_in_grouping}. "
                    f"Inactive members should not be included."
                )
                
            finally:
                db.session.remove()
                db.drop_all()

class TestPackageCRUDRoundTrip:
    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        duration_months=st.integers(min_value=1, max_value=24),
        price=st.integers(min_value=1000, max_value=100000000),
        description=st.text(max_size=200),
    )
    @settings(max_examples=100)
    def test_package_create_and_retrieve_returns_same_values(
        self,
        name: str,
        duration_months: int,
        price: int,
        description: str,
    ) -> None:
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                package = Package(
                    name=name.strip(),
                    duration_months=duration_months,
                    price=price,
                    description=description.strip() if description.strip() else None,
                )
                db.session.add(package)
                db.session.commit()
                package_id = package.id
                
                retrieved = Package.query.get(package_id)
                
                assert retrieved is not None, "Package was not saved"
                assert retrieved.name == name.strip(), (
                    f"Name mismatch: {retrieved.name} != {name.strip()}"
                )
                assert retrieved.duration_months == duration_months, (
                    f"Duration mismatch: {retrieved.duration_months} != {duration_months}"
                )
                assert retrieved.price == price, (
                    f"Price mismatch: {retrieved.price} != {price}"
                )
                expected_desc = description.strip() if description.strip() else None
                assert retrieved.description == expected_desc, (
                    f"Description mismatch: {retrieved.description} != {expected_desc}"
                )
                
            finally:
                db.session.remove()
                db.drop_all()

    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        duration_months=st.integers(min_value=1, max_value=24),
        price=st.integers(min_value=1000, max_value=100000000),
        description=st.text(max_size=200),
        new_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        new_duration=st.integers(min_value=1, max_value=24),
        new_price=st.integers(min_value=1000, max_value=100000000),
        new_description=st.text(max_size=200),
    )
    @settings(max_examples=100)
    def test_package_update_and_retrieve_returns_new_values(
        self,
        name: str,
        duration_months: int,
        price: int,
        description: str,
        new_name: str,
        new_duration: int,
        new_price: int,
        new_description: str,
    ) -> None:
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                package = Package(
                    name=name.strip(),
                    duration_months=duration_months,
                    price=price,
                    description=description.strip() if description.strip() else None,
                )
                db.session.add(package)
                db.session.commit()
                package_id = package.id
                
                package.name = new_name.strip()
                package.duration_months = new_duration
                package.price = new_price
                package.description = new_description.strip() if new_description.strip() else None
                db.session.commit()
                
                retrieved = Package.query.get(package_id)
                
                assert retrieved is not None, "Package was not found after update"
                assert retrieved.name == new_name.strip(), (
                    f"Updated name mismatch: {retrieved.name} != {new_name.strip()}"
                )
                assert retrieved.duration_months == new_duration, (
                    f"Updated duration mismatch: {retrieved.duration_months} != {new_duration}"
                )
                assert retrieved.price == new_price, (
                    f"Updated price mismatch: {retrieved.price} != {new_price}"
                )
                expected_desc = new_description.strip() if new_description.strip() else None
                assert retrieved.description == expected_desc, (
                    f"Updated description mismatch: {retrieved.description} != {expected_desc}"
                )
                
            finally:
                db.session.remove()
                db.drop_all()

class TestPackageDeletionWithoutInvoices:
    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        duration_months=st.integers(min_value=1, max_value=24),
        price=st.integers(min_value=1000, max_value=100000000),
    )
    @settings(max_examples=100)
    def test_package_without_invoices_can_be_deleted(
        self,
        name: str,
        duration_months: int,
        price: int,
    ) -> None:
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                package = Package(
                    name=name.strip(),
                    duration_months=duration_months,
                    price=price,
                    description=None,
                )
                db.session.add(package)
                db.session.commit()
                package_id = package.id
                
                invoice_count = Invoice.query.filter_by(package_id=package_id).count()
                assert invoice_count == 0, "Package should have no invoices"
                
                db.session.delete(package)
                db.session.commit()
                
                deleted_package = Package.query.get(package_id)
                assert deleted_package is None, (
                    f"Package {package_id} should have been deleted but still exists"
                )
                
            finally:
                db.session.remove()
                db.drop_all()

class TestPackageDeletionWithInvoicesFails:
    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        duration_months=st.integers(min_value=1, max_value=24),
        price=st.integers(min_value=1000, max_value=100000000),
        num_invoices=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=100)
    def test_package_with_invoices_cannot_be_deleted(
        self,
        name: str,
        duration_months: int,
        price: int,
        num_invoices: int,
    ) -> None:
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                package = Package(
                    name=name.strip(),
                    duration_months=duration_months,
                    price=price,
                    description=None,
                )
                db.session.add(package)
                db.session.commit()
                package_id = package.id
                
                member = Member(
                    full_name="Test Member",
                    gender="Male",
                    dob=date(1990, 1, 1),
                    phone="0123456789",
                    email="test@example.com",
                    registration_date=datetime.utcnow(),
                    active_until=date.today() + timedelta(days=30),
                )
                db.session.add(member)
                db.session.commit()
                
                for i in range(num_invoices):
                    invoice = Invoice(
                        member_id=member.id,
                        package_id=package_id,
                        amount=price,
                    )
                    db.session.add(invoice)
                db.session.commit()
                
                invoice_count = Invoice.query.filter_by(package_id=package_id).count()
                assert invoice_count == num_invoices, (
                    f"Expected {num_invoices} invoices, got {invoice_count}"
                )
                
                has_invoices = Invoice.query.filter_by(package_id=package_id).count() > 0
                
                assert has_invoices, "Package should have invoices preventing deletion"
                
                existing_package = Package.query.get(package_id)
                assert existing_package is not None, (
                    f"Package {package_id} should still exist after failed deletion attempt"
                )
                assert existing_package.name == name.strip(), (
                    "Package data should be unchanged"
                )
                
            finally:
                db.session.remove()
                db.drop_all()

class TestExerciseCRUDRoundTrip:
    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        description=st.text(max_size=200),
        body_part=st.text(max_size=50),
    )
    @settings(max_examples=100)
    def test_exercise_create_and_retrieve_returns_same_values(
        self,
        name: str,
        description: str,
        body_part: str,
    ) -> None:
        app = create_app(TestConfig)

        with app.app_context():
            db.create_all()

            try:
                exercise = Exercise(
                    name=name.strip(),
                    description=description.strip() if description.strip() else None,
                    body_part=body_part.strip() if body_part.strip() else None,
                )
                db.session.add(exercise)
                db.session.commit()
                exercise_id = exercise.id

                retrieved = Exercise.query.get(exercise_id)

                assert retrieved is not None, "Exercise was not saved"
                assert retrieved.name == name.strip(), (
                    f"Name mismatch: {retrieved.name} != {name.strip()}"
                )
                expected_desc = description.strip() if description.strip() else None
                assert retrieved.description == expected_desc, (
                    f"Description mismatch: {retrieved.description} != {expected_desc}"
                )
                expected_body_part = body_part.strip() if body_part.strip() else None
                assert retrieved.body_part == expected_body_part, (
                    f"Body part mismatch: {retrieved.body_part} != {expected_body_part}"
                )

            finally:
                db.session.remove()
                db.drop_all()

    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        description=st.text(max_size=200),
        body_part=st.text(max_size=50),
        new_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        new_description=st.text(max_size=200),
        new_body_part=st.text(max_size=50),
    )
    @settings(max_examples=100)
    def test_exercise_update_and_retrieve_returns_new_values(
        self,
        name: str,
        description: str,
        body_part: str,
        new_name: str,
        new_description: str,
        new_body_part: str,
    ) -> None:
        app = create_app(TestConfig)

        with app.app_context():
            db.create_all()

            try:
                exercise = Exercise(
                    name=name.strip(),
                    description=description.strip() if description.strip() else None,
                    body_part=body_part.strip() if body_part.strip() else None,
                )
                db.session.add(exercise)
                db.session.commit()
                exercise_id = exercise.id

                exercise.name = new_name.strip()
                exercise.description = new_description.strip() if new_description.strip() else None
                exercise.body_part = new_body_part.strip() if new_body_part.strip() else None
                db.session.commit()

                retrieved = Exercise.query.get(exercise_id)

                assert retrieved is not None, "Exercise was not found after update"
                assert retrieved.name == new_name.strip(), (
                    f"Updated name mismatch: {retrieved.name} != {new_name.strip()}"
                )
                expected_desc = new_description.strip() if new_description.strip() else None
                assert retrieved.description == expected_desc, (
                    f"Updated description mismatch: {retrieved.description} != {expected_desc}"
                )
                expected_body_part = new_body_part.strip() if new_body_part.strip() else None
                assert retrieved.body_part == expected_body_part, (
                    f"Updated body part mismatch: {retrieved.body_part} != {expected_body_part}"
                )

            finally:
                db.session.remove()
                db.drop_all()

class TestExerciseDeletionWithoutPlans:
    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        description=st.text(max_size=200),
        body_part=st.text(max_size=50),
    )
    @settings(max_examples=100)
    def test_exercise_without_plans_can_be_deleted(
        self,
        name: str,
        description: str,
        body_part: str,
    ) -> None:
        app = create_app(TestConfig)

        with app.app_context():
            db.create_all()

            try:
                exercise = Exercise(
                    name=name.strip(),
                    description=description.strip() if description.strip() else None,
                    body_part=body_part.strip() if body_part.strip() else None,
                )
                db.session.add(exercise)
                db.session.commit()
                exercise_id = exercise.id

                detail_count = WorkoutDetail.query.filter_by(exercise_id=exercise_id).count()
                assert detail_count == 0, "Exercise should have no workout details"

                db.session.delete(exercise)
                db.session.commit()

                deleted_exercise = Exercise.query.get(exercise_id)
                assert deleted_exercise is None, (
                    f"Exercise {exercise_id} should have been deleted but still exists"
                )

            finally:
                db.session.remove()
                db.drop_all()

class TestExerciseDeletionWithPlansFails:
    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        num_details=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=100, deadline=None)
    def test_exercise_with_plans_cannot_be_deleted(
        self,
        name: str,
        num_details: int,
    ) -> None:
        app = create_app(TestConfig)

        with app.app_context():
            db.create_all()

            try:
                exercise = Exercise(
                    name=name.strip(),
                    description="Test exercise",
                    body_part="Test body part",
                )
                db.session.add(exercise)
                db.session.commit()
                exercise_id = exercise.id

                trainer = User(
                    username="trainer_test",
                    email="trainer@test.com",
                    role="trainer",
                )
                trainer.set_password("password123")
                db.session.add(trainer)
                db.session.commit()

                member = Member(
                    full_name="Test Member",
                    gender="Male",
                    dob=date(1990, 1, 1),
                    phone="0123456789",
                    email="member@test.com",
                    registration_date=datetime.utcnow(),
                    active_until=date.today() + timedelta(days=30),
                )
                db.session.add(member)
                db.session.commit()

                workout_plan = WorkoutPlan(
                    member_id=member.id,
                    trainer_id=trainer.id,
                    notes="Test plan",
                )
                db.session.add(workout_plan)
                db.session.commit()

                for i in range(num_details):
                    detail = WorkoutDetail(
                        plan_id=workout_plan.id,
                        exercise_id=exercise_id,
                        sets=3,
                        reps="10",
                        schedule_day=f"Day {i + 1}",
                    )
                    db.session.add(detail)
                db.session.commit()

                detail_count = WorkoutDetail.query.filter_by(exercise_id=exercise_id).count()
                assert detail_count == num_details, (
                    f"Expected {num_details} workout details, got {detail_count}"
                )

                has_details = WorkoutDetail.query.filter_by(exercise_id=exercise_id).count() > 0

                assert has_details, "Exercise should have workout details preventing deletion"

                existing_exercise = Exercise.query.get(exercise_id)
                assert existing_exercise is not None, (
                    f"Exercise {exercise_id} should still exist after failed deletion attempt"
                )
                assert existing_exercise.name == name.strip(), (
                    "Exercise data should be unchanged"
                )

            finally:
                db.session.remove()
                db.drop_all()

class TestConfigSettingPersistence:
    @given(
        max_training_days=st.integers(min_value=1, max_value=7),
    )
    @settings(max_examples=100)
    def test_config_setting_persistence_round_trip(
        self,
        max_training_days: int,
    ) -> None:
        from app.models import SystemConfig
        
        app = create_app(TestConfig)

        with app.app_context():
            db.create_all()

            try:
                SystemConfig.set_config(
                    key="max_training_days",
                    value=str(max_training_days),
                    description="Maximum training days per week"
                )

                retrieved_value = SystemConfig.get_config("max_training_days")

                assert retrieved_value is not None, "Config value was not saved"
                assert retrieved_value == str(max_training_days), (
                    f"Config value mismatch: {retrieved_value} != {max_training_days}"
                )

            finally:
                db.session.remove()
                db.drop_all()

    @given(
        initial_value=st.integers(min_value=1, max_value=7),
        new_value=st.integers(min_value=1, max_value=7),
    )
    @settings(max_examples=100)
    def test_config_setting_update_overwrites_previous_value(
        self,
        initial_value: int,
        new_value: int,
    ) -> None:
        from app.models import SystemConfig
        
        app = create_app(TestConfig)

        with app.app_context():
            db.create_all()

            try:
                SystemConfig.set_config(
                    key="max_training_days",
                    value=str(initial_value),
                    description="Maximum training days per week"
                )

                initial_retrieved = SystemConfig.get_config("max_training_days")
                assert initial_retrieved == str(initial_value), (
                    f"Initial value mismatch: {initial_retrieved} != {initial_value}"
                )

                SystemConfig.set_config(
                    key="max_training_days",
                    value=str(new_value),
                    description="Maximum training days per week"
                )

                new_retrieved = SystemConfig.get_config("max_training_days")
                assert new_retrieved == str(new_value), (
                    f"Updated value mismatch: {new_retrieved} != {new_value}"
                )

            finally:
                db.session.remove()
                db.drop_all()

class TestWorkoutPlanMaxDaysValidation:
    @given(
        max_training_days=st.integers(min_value=1, max_value=6),
        extra_days=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=100, deadline=None)
    def test_plan_exceeding_max_days_is_rejected(
        self,
        max_training_days: int,
        extra_days: int,
    ) -> None:
        from app.models import SystemConfig
        
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                SystemConfig.set_config(
                    key="max_training_days",
                    value=str(max_training_days),
                    description="Maximum training days per week"
                )
                
                trainer = User(
                    username="trainer_test",
                    email="trainer@test.com",
                    role="trainer",
                )
                trainer.set_password("password123")
                db.session.add(trainer)
                db.session.commit()
                
                member = Member(
                    full_name="Test Member",
                    gender="Male",
                    dob=date(1990, 1, 1),
                    phone="0123456789",
                    email="member@test.com",
                    registration_date=datetime.utcnow(),
                    active_until=date.today() + timedelta(days=30),
                )
                db.session.add(member)
                db.session.commit()
                
                exercise = Exercise(
                    name="Test Exercise",
                    description="Test description",
                    body_part="Test body part",
                )
                db.session.add(exercise)
                db.session.commit()
                
                all_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                num_days_to_use = max_training_days + extra_days
                days_to_use = all_days[:min(num_days_to_use, 7)]
                
                unique_days = set()
                for day in days_to_use:
                    unique_days.add(day.strip().lower())
                
                assert len(unique_days) > max_training_days, (
                    f"Test setup error: {len(unique_days)} days should exceed max {max_training_days}"
                )
                
                max_training_days_config = int(SystemConfig.get_config("max_training_days", "6"))
                plan_should_be_rejected = len(unique_days) > max_training_days_config
                
                assert plan_should_be_rejected, (
                    f"Plan with {len(unique_days)} unique days should be rejected "
                    f"when max is {max_training_days_config}"
                )
                
            finally:
                db.session.remove()
                db.drop_all()

    @given(
        max_training_days=st.integers(min_value=2, max_value=7),
        num_days_to_use=st.integers(min_value=1, max_value=7),
    )
    @settings(max_examples=100, deadline=None)
    def test_plan_within_max_days_is_accepted(
        self,
        max_training_days: int,
        num_days_to_use: int,
    ) -> None:
        assume(num_days_to_use <= max_training_days)
        
        from app.models import SystemConfig
        
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                SystemConfig.set_config(
                    key="max_training_days",
                    value=str(max_training_days),
                    description="Maximum training days per week"
                )
                
                all_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                days_to_use = all_days[:num_days_to_use]
                
                unique_days = set()
                for day in days_to_use:
                    unique_days.add(day.strip().lower())
                
                assert len(unique_days) <= max_training_days, (
                    f"Test setup error: {len(unique_days)} days should be within max {max_training_days}"
                )
                
                max_training_days_config = int(SystemConfig.get_config("max_training_days", "6"))
                plan_should_be_accepted = len(unique_days) <= max_training_days_config
                
                assert plan_should_be_accepted, (
                    f"Plan with {len(unique_days)} unique days should be accepted "
                    f"when max is {max_training_days_config}"
                )
                
            finally:
                db.session.remove()
                db.drop_all()

    @given(
        max_training_days=st.integers(min_value=1, max_value=6),
        extra_days=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=100, deadline=None)
    def test_validation_error_message_contains_max_days(
        self,
        max_training_days: int,
        extra_days: int,
    ) -> None:
        from app.models import SystemConfig
        
        app = create_app(TestConfig)
        
        with app.app_context():
            db.create_all()
            
            try:
                SystemConfig.set_config(
                    key="max_training_days",
                    value=str(max_training_days),
                    description="Maximum training days per week"
                )
                
                all_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                num_days_to_use = max_training_days + extra_days
                days_to_use = all_days[:min(num_days_to_use, 7)]
                
                unique_days = set()
                for day in days_to_use:
                    unique_days.add(day.strip().lower())
                
                max_training_days_config = int(SystemConfig.get_config("max_training_days", "6"))
                
                if len(unique_days) > max_training_days_config:
                    error_message = (
                        f"Workout plan exceeds maximum {max_training_days_config} training days per week. "
                        f"You have {len(unique_days)} unique days."
                    )
                    
                    assert str(max_training_days_config) in error_message, (
                        f"Error message should contain max days value {max_training_days_config}"
                    )
                    assert str(len(unique_days)) in error_message, (
                        f"Error message should contain actual days count {len(unique_days)}"
                    )
                
            finally:
                db.session.remove()
                db.drop_all()
