import pytest
from app.api.v1.deps.auth import check_permission
from app.models.models import User, Role, Permission, RolePermission, UserRole


def test_superuser_bypass(db_session):
    user = User(username="root", password_hash="x", is_superuser=True, is_active=True)
    db_session.add(user)
    db_session.commit()
    check_permission(user, "any.permission", db=db_session)


def test_rbac_denies_without_permission(db_session):
    user = User(username="user1", password_hash="x", is_superuser=False, is_active=True)
    role = Role(name="viewer", scope="global")
    perm = Permission(code="product.read")
    db_session.add_all([user, role, perm])
    db_session.commit()
    rp = RolePermission(role_id=role.id, permission_id=perm.id)
    ur = UserRole(user_id=user.id, role_id=role.id)
    db_session.add_all([rp, ur])
    db_session.commit()
    with pytest.raises(Exception):
        check_permission(user, "product.write", db=db_session)
