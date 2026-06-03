import streamlit as st
import hashlib
import json
import os
import re
import secrets
import logging
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timedelta
import jwt
from email.mime.text import MIMEText
import smtplib
import threading

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedAuthSystem:
    """
    Advanced Authentication System with enhanced security features:
    - JWT tokens for session management
    - Password strength validation
    - Rate limiting
    - Email verification
    - Account locking
    - Session management
    - Audit logging
    """
    
    def __init__(self, users_file: str = "data/users.json", secret_key: str = None):
        self.users_file = users_file
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.failed_attempts_file = "data/failed_attempts.json"
        self.sessions_file = "data/sessions.json"
        self.audit_log_file = "data/audit.log"
        
        # Security settings
        self.max_login_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        self.session_duration = timedelta(hours=24)
        
        # Initialize directories and files
        self._initialize_system()
        self._initialize_default_users()
        
        logger.info("🔐 Advanced Authentication System initialized")

    def _initialize_system(self):
        """Initialize required directories and files"""
        os.makedirs("data", exist_ok=True)
        
        # Initialize failed attempts tracker
        if not os.path.exists(self.failed_attempts_file):
            self._save_data({}, self.failed_attempts_file)
        
        # Initialize sessions tracker
        if not os.path.exists(self.sessions_file):
            self._save_data({}, self.sessions_file)

    def _initialize_default_users(self):
        """Initialize default users with enhanced security"""
        if not os.path.exists(self.users_file):
            default_users = {
                "admin": {
                    "password": self._hash_password("Admin123!"),
                    "role": "admin",
                    "email": "admin@company.com",
                    "created_at": datetime.now().isoformat(),
                    "last_login": None,
                    "is_active": True,
                    "email_verified": True
                },
                "manager": {
                    "password": self._hash_password("Manager123!"),
                    "role": "manager", 
                    "email": "manager@company.com",
                    "created_at": datetime.now().isoformat(),
                    "last_login": None,
                    "is_active": True,
                    "email_verified": True
                },
                "user1": {
                    "password": self._hash_password("User123!"),
                    "role": "user",
                    "email": "user1@company.com",
                    "created_at": datetime.now().isoformat(),
                    "last_login": None,
                    "is_active": True,
                    "email_verified": True
                }
            }
            self._save_users(default_users)
            self._audit_log("SYSTEM", "Default users initialized")

    def _hash_password(self, password: str) -> str:
        """Enhanced password hashing with salt"""
        salt = "advanced_rag_system_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()

    def _validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"
        
        return True, "Password is strong"

    def _load_users(self) -> Dict[str, Any]:
        """Load users with error handling"""
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_users(self, users: Dict[str, Any]):
        """Save users with backup"""
        try:
            # Create backup
            if os.path.exists(self.users_file):
                backup_file = f"{self.users_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                with open(self.users_file, 'r') as src, open(backup_file, 'w') as dst:
                    dst.write(src.read())
            
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving users: {e}")
            raise

    def _save_data(self, data: Dict, filepath: str):
        """Generic data saver"""
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving data to {filepath}: {e}")

    def _load_data(self, filepath: str) -> Dict:
        """Generic data loader"""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _audit_log(self, username: str, action: str, details: str = ""):
        """Log security events"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "username": username,
            "action": action,
            "details": details
        }
        
        try:
            with open(self.audit_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Audit log error: {e}")

    def _is_account_locked(self, username: str) -> Tuple[bool, Optional[str]]:
        """Check if account is locked due to failed attempts"""
        failed_attempts = self._load_data(self.failed_attempts_file)
        
        if username in failed_attempts:
            user_attempts = failed_attempts[username]
            last_attempt = datetime.fromisoformat(user_attempts["last_attempt"])
            
            if (datetime.now() - last_attempt) < self.lockout_duration:
                if user_attempts["count"] >= self.max_login_attempts:
                    unlock_time = last_attempt + self.lockout_duration
                    return True, f"Account locked until {unlock_time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        return False, None

    def _record_failed_attempt(self, username: str):
        """Record failed login attempt"""
        failed_attempts = self._load_data(self.failed_attempts_file)
        
        if username not in failed_attempts:
            failed_attempts[username] = {"count": 0, "last_attempt": None}
        
        failed_attempts[username]["count"] += 1
        failed_attempts[username]["last_attempt"] = datetime.now().isoformat()
        
        self._save_data(failed_attempts, self.failed_attempts_file)
        self._audit_log(username, "FAILED_LOGIN_ATTEMPT", f"Attempt {failed_attempts[username]['count']}")

    def _clear_failed_attempts(self, username: str):
        """Clear failed attempts on successful login"""
        failed_attempts = self._load_data(self.failed_attempts_file)
        
        if username in failed_attempts:
            del failed_attempts[username]
            self._save_data(failed_attempts, self.failed_attempts_file)

    def _generate_jwt_token(self, username: str, role: str) -> str:
        """Generate JWT token for session management"""
        payload = {
            "username": username,
            "role": role,
            "exp": datetime.now() + self.session_duration,
            "iat": datetime.now()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def _verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Enhanced authentication with security features
        
        Returns:
            Tuple[success, role, error_message]
        """
        # Check if account is locked
        is_locked, lock_message = self._is_account_locked(username)
        if is_locked:
            self._audit_log(username, "LOGIN_FAILED_LOCKED", lock_message)
            return False, None, f"Account locked: {lock_message}"

        users = self._load_users()
        
        if username not in users:
            self._record_failed_attempt(username)
            self._audit_log(username, "LOGIN_FAILED_USER_NOT_FOUND")
            return False, None, "Invalid username or password"
        
        user = users[username]
        
        # Check if account is active
        if not user.get("is_active", True):
            self._audit_log(username, "LOGIN_FAILED_ACCOUNT_INACTIVE")
            return False, None, "Account is deactivated"
        
        # Verify password
        hashed_input = self._hash_password(password)
        if user["password"] == hashed_input:
            # Successful login
            self._clear_failed_attempts(username)
            
            # Update last login
            user["last_login"] = datetime.now().isoformat()
            users[username] = user
            self._save_users(users)
            
            # Generate token
            token = self._generate_jwt_token(username, user["role"])
            
            self._audit_log(username, "LOGIN_SUCCESS")
            return True, user["role"], token
        else:
            # Failed login
            self._record_failed_attempt(username)
            self._audit_log(username, "LOGIN_FAILED_INVALID_PASSWORD")
            return False, None, "Invalid username or password"

    def create_user(self, username: str, password: str, role: str, email: str = "") -> Tuple[bool, str]:
        """Create new user with enhanced validation"""
        # Validate username
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            return False, "Username must be 3-20 characters and contain only letters, numbers, and underscores"
        
        # Validate password strength
        is_valid, msg = self._validate_password_strength(password)
        if not is_valid:
            return False, f"Weak password: {msg}"
        
        # Validate email
        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return False, "Invalid email format"
        
        users = self._load_users()
        
        if username in users:
            return False, "Username already exists"
        
        users[username] = {
            "password": self._hash_password(password),
            "role": role,
            "email": email,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "is_active": True,
            "email_verified": False
        }
        
        self._save_users(users)
        self._audit_log("SYSTEM", "USER_CREATED", f"Username: {username}, Role: {role}")
        
        return True, f"User '{username}' created successfully"

    def update_user_role(self, username: str, new_role: str) -> Tuple[bool, str]:
        """Update user role"""
        users = self._load_users()
        
        if username not in users:
            return False, "User not found"
        
        old_role = users[username]["role"]
        users[username]["role"] = new_role
        self._save_users(users)
        
        self._audit_log("SYSTEM", "USER_ROLE_UPDATED", f"Username: {username}, {old_role} -> {new_role}")
        return True, f"User '{username}' role updated to '{new_role}'"

    def delete_user(self, username: str) -> Tuple[bool, str]:
        """Delete user account"""
        users = self._load_users()
        
        if username not in users:
            return False, "User not found"
        
        # Prevent deleting the last admin
        if users[username]["role"] == "admin":
            admin_count = sum(1 for user in users.values() if user["role"] == "admin")
            if admin_count <= 1:
                return False, "Cannot delete the last admin account"
        
        del users[username]
        self._save_users(users)
        
        self._audit_log("SYSTEM", "USER_DELETED", f"Username: {username}")
        return True, f"User '{username}' deleted successfully"

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password"""
        users = self._load_users()
        
        if username not in users:
            return False, "User not found"
        
        # Verify old password
        hashed_old = self._hash_password(old_password)
        if users[username]["password"] != hashed_old:
            return False, "Current password is incorrect"
        
        # Validate new password
        is_valid, msg = self._validate_password_strength(new_password)
        if not is_valid:
            return False, f"Weak new password: {msg}"
        
        users[username]["password"] = self._hash_password(new_password)
        self._save_users(users)
        
        self._audit_log(username, "PASSWORD_CHANGED")
        return True, "Password changed successfully"

    def get_all_users(self) -> Dict[str, Any]:
        """Get all users (excluding passwords for security)"""
        users = self._load_users()
        safe_users = {}
        
        for username, data in users.items():
            safe_users[username] = {k: v for k, v in data.items() if k != "password"}
        
        return safe_users

    def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics"""
        users = self._load_users()
        stats = {
            "total_users": len(users),
            "active_users": sum(1 for u in users.values() if u.get("is_active", True)),
            "roles": {},
            "recent_logins": 0
        }
        
        # Count by role
        for user in users.values():
            role = user.get("role", "user")
            stats["roles"][role] = stats["roles"].get(role, 0) + 1
            
            # Count recent logins (last 7 days)
            if user.get("last_login"):
                last_login = datetime.fromisoformat(user["last_login"])
                if (datetime.now() - last_login) < timedelta(days=7):
                    stats["recent_logins"] += 1
        
        return stats

    def validate_session(self, token: str) -> Tuple[bool, Optional[Dict]]:
        """Validate JWT session token"""
        payload = self._verify_jwt_token(token)
        if not payload:
            return False, None
        
        # Check if user still exists and is active
        users = self._load_users()
        username = payload.get("username")
        
        if username not in users or not users[username].get("is_active", True):
            return False, None
        
        return True, payload

    def reset_user_password(self, target_username: str, new_password: str, performed_by: str) -> Tuple[bool, str]:
        """Reset password for a user (called by manager/admin)"""
        users = self._load_users()

        if target_username not in users:
            return False, "User not found"

        # Validate new password strength
        is_valid, msg = self._validate_password_strength(new_password)
        if not is_valid:
            return False, f"Weak password: {msg}"

        users[target_username]["password"] = self._hash_password(new_password)
        self._save_users(users)
        self._audit_log(performed_by, "PASSWORD_RESET", f"Reset password for: {target_username}")
        return True, f"Password for '{target_username}' has been reset successfully"

    def toggle_user_active(self, target_username: str, performed_by: str) -> Tuple[bool, str]:
        """Toggle active/inactive status for a user"""
        users = self._load_users()

        if target_username not in users:
            return False, "User not found"

        current_status = users[target_username].get("is_active", True)
        new_status = not current_status
        users[target_username]["is_active"] = new_status
        self._save_users(users)

        action = "ACTIVATED" if new_status else "DEACTIVATED"
        self._audit_log(performed_by, f"USER_{action}", f"User: {target_username}")
        status_word = "activated" if new_status else "deactivated"
        return True, f"User '{target_username}' has been {status_word}"


def initialize_session_state():
    """Initialize advanced session state management"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'login_attempted' not in st.session_state:
        st.session_state.login_attempted = False
    if 'jwt_token' not in st.session_state:
        st.session_state.jwt_token = None
    if 'show_user_management' not in st.session_state:
        st.session_state.show_user_management = False
    if 'show_security_logs' not in st.session_state:
        st.session_state.show_security_logs = False


def render_login(auth_system: AdvancedAuthSystem):
    """Render advanced login interface"""
    # Centered RAG System title at the top
    st.markdown("""
        <div style='text-align:center; padding:20px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius:10px; margin-bottom:30px;'>
            <h1 style='color:white; margin:0;'>🚀 Enterprise RAG System</h1>
            <p style='color:white; opacity:0.9; margin:5px 0 0 0;'>Advanced AI-Powered Document Intelligence</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Login form in a card-like container
    with st.container():
        st.markdown("### 🔐 Secure Login")
        st.write("Please enter your credentials to access the system:")
        
        with st.form("login_form", clear_on_submit=False):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                username = st.text_input(
                    "**Username**",
                    placeholder="Enter your username",
                    help="Your unique username"
                )
            
            with col2:
                password = st.text_input(
                    "**Password**", 
                    type="password",
                    placeholder="Enter your password",
                    help="Your secure password"
                )
            
            # Additional options
            col3, col4 = st.columns([2, 1])
            with col3:
                remember_me = st.checkbox("Remember me", value=False)
            
            submitted = st.form_submit_button(
                "🚀 **Login to System**",
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                st.session_state.login_attempted = True
                if username and password:
                    with st.spinner("🔒 Authenticating..."):
                        success, role, message = auth_system.authenticate(username, password)
                        
                        if success:
                            st.session_state.authenticated = True
                            st.session_state.user_role = role
                            st.session_state.current_user = username
                            st.session_state.jwt_token = message
                            
                            st.success(f"✅ Welcome back, **{username}**!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                else:
                    st.warning("⚠️ Please enter both username and password")

    st.markdown("---")
    
    # Demo credentials in an expandable section
    with st.expander("🔑 Demo Credentials", expanded=False):
        st.info("Use these credentials to test the system:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**👑 Admin Account**")
            st.code("Username: admin\nPassword: Admin123!")
            st.caption("Full system access")
        
        with col2:
            st.markdown("**👔 Manager Account**")
            st.code("Username: manager\nPassword: Manager123!")
            st.caption("Management privileges")
        
        with col3:
            st.markdown("**👤 User Account**")
            st.code("Username: user1\nPassword: User123!")
            st.caption("Standard user access")


def render_user_management(auth_system: AdvancedAuthSystem):
    """Render user management interface for admins"""
    st.subheader("👥 User Management")
    
    # User statistics
    stats = auth_system.get_user_stats()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", stats["total_users"])
    with col2:
        st.metric("Active Users", stats["active_users"])
    with col3:
        st.metric("Recent Logins", stats["recent_logins"])
    with col4:
        st.metric("Roles", len(stats["roles"]))
    
    # Add new user form
    with st.expander("➕ Add New User", expanded=False):
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username", placeholder="Enter username")
                new_email = st.text_input("Email", placeholder="user@company.com")
            
            with col2:
                new_password = st.text_input("Password", type="password", placeholder="Enter password")
                new_role = st.selectbox("Role", ["user", "manager", "admin"])
            
            if st.form_submit_button("Create User", use_container_width=True):
                if new_username and new_password:
                    success, message = auth_system.create_user(new_username, new_password, new_role, new_email)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please fill all required fields")
    
    # Users list
    st.subheader("📋 User List")
    users = auth_system.get_all_users()
    
    if not users:
        st.info("No users found")
        return
    
    for username, user_data in users.items():
        with st.expander(f"👤 {username} - {user_data.get('role', 'user').upper()}", expanded=False):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"**Email:** {user_data.get('email', 'N/A')}")
                st.write(f"**Created:** {user_data.get('created_at', 'N/A')}")
                st.write(f"**Last Login:** {user_data.get('last_login', 'Never')}")
                st.write(f"**Status:** {'✅ Active' if user_data.get('is_active', True) else '❌ Inactive'}")
            
            with col2:
                if username != st.session_state.current_user:
                    new_role = st.selectbox(
                        "Role",
                        ["user", "manager", "admin"],
                        index=["user", "manager", "admin"].index(user_data.get('role', 'user')),
                        key=f"role_{username}"
                    )
                    if st.button("Update Role", key=f"update_{username}"):
                        success, message = auth_system.update_user_role(username, new_role)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
            
            with col3:
                if username != st.session_state.current_user and username != "admin":
                    if st.button("🗑️ Delete", key=f"delete_{username}", type="secondary"):
                        success, message = auth_system.delete_user(username)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)


def render_manager_portal(auth_system: AdvancedAuthSystem):
    """Full Manager Portal - Create & manage user credentials"""

    st.markdown("""
        <div style='
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            padding: 24px 32px;
            border-radius: 16px;
            margin-bottom: 28px;
            border: 1px solid rgba(100,180,255,0.15);
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        '>
            <h2 style='color:#64b4ff; margin:0; font-size:1.8rem;'>👔 Manager Portal</h2>
            <p style='color:#a0b4cc; margin:6px 0 0 0; font-size:0.95rem;'>
                Create user accounts, manage credentials, and control access.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── Stats Bar ──────────────────────────────────────────────────────────
    stats = auth_system.get_user_stats()
    all_users = auth_system.get_all_users()
    # Manager can only see non-admin users
    managed_users = {u: d for u, d in all_users.items() if d.get("role") != "admin"}

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Managed Users", len(managed_users))
    with col2:
        active_count = sum(1 for d in managed_users.values() if d.get("is_active", True))
        st.metric("✅ Active", active_count)
    with col3:
        inactive_count = len(managed_users) - active_count
        st.metric("🔴 Inactive", inactive_count)
    with col4:
        recent = sum(
            1 for d in managed_users.values()
            if d.get("last_login") and
            (datetime.now() - datetime.fromisoformat(d["last_login"])).days <= 7
        )
        st.metric("🕐 Recent Logins", recent)

    st.markdown("---")

    # ── Tabs ───────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["➕ Create User", "🔑 Manage Credentials", "📋 User List"])

    # ── TAB 1 : Create User ────────────────────────────────────────────────
    with tab1:
        st.markdown("### ➕ Create New User Account")
        st.info(
            "📌 As a manager you can create **user** accounts only. "
            "Contact an administrator to create manager accounts."
        )

        with st.form("manager_create_user_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                new_username = st.text_input(
                    "👤 Username *",
                    placeholder="e.g. john_doe",
                    help="3–20 characters: letters, numbers, underscores"
                )
                new_email = st.text_input(
                    "📧 Email",
                    placeholder="user@company.com"
                )
            with col_b:
                new_password = st.text_input(
                    "🔒 Password *",
                    type="password",
                    placeholder="Min 8 chars, upper/lower/digit/special"
                )
                confirm_password = st.text_input(
                    "🔒 Confirm Password *",
                    type="password",
                    placeholder="Repeat password"
                )

            # Password strength hint
            st.caption(
                "🛡️ **Password rules:** Min 8 chars · Uppercase · Lowercase · Digit · Special char (!@#$%^&*)"
            )

            submitted = st.form_submit_button(
                "🚀 Create User Account",
                use_container_width=True,
                type="primary"
            )

            if submitted:
                if not new_username or not new_password or not confirm_password:
                    st.error("❌ Username and both password fields are required.")
                elif new_password != confirm_password:
                    st.error("❌ Passwords do not match.")
                else:
                    success, message = auth_system.create_user(
                        new_username, new_password, "user", new_email
                    )
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                        # Show credential card
                        st.markdown("""
                            <div style='
                                background:#0d2137;
                                border:1px solid #2563eb;
                                border-radius:10px;
                                padding:16px 20px;
                                margin-top:12px;
                            '>
                                <b style='color:#64b4ff'>📋 Credentials to share with user:</b><br><br>
                        """, unsafe_allow_html=True)
                        st.code(f"Username : {new_username}\nPassword : {new_password}\nRole     : user", language="text")
                        st.markdown("</div>", unsafe_allow_html=True)
                        st.warning("⚠️ Share these credentials securely. The password cannot be retrieved later.")
                    else:
                        st.error(f"❌ {message}")

    # ── TAB 2 : Manage Credentials ─────────────────────────────────────────
    with tab2:
        st.markdown("### 🔑 Reset User Password")
        st.caption("You can reset passwords for any non-admin user account.")

        if not managed_users:
            st.info("No users to manage yet. Create one in the **Create User** tab.")
        else:
            user_options = list(managed_users.keys())
            selected_user = st.selectbox(
                "Select user to manage",
                user_options,
                key="mgr_select_reset_user"
            )

            if selected_user:
                u_data = managed_users[selected_user]
                # User info card
                status_badge = (
                    "🟢 Active" if u_data.get("is_active", True) else "🔴 Inactive"
                )
                st.markdown(f"""
                    <div style='
                        background:#0d2137;
                        border-radius:10px;
                        padding:14px 18px;
                        border:1px solid rgba(100,180,255,0.2);
                        margin-bottom:16px;
                    '>
                        <b style='color:#64b4ff'>👤 {selected_user}</b>
                        &nbsp;&nbsp;
                        <span style='color:#a0b4cc; font-size:0.85rem;'>{status_badge}</span><br>
                        <span style='color:#a0b4cc; font-size:0.85rem;'>
                            Role: {u_data.get('role','user').capitalize()} &nbsp;|
                            Email: {u_data.get('email','N/A')} &nbsp;|
                            Last login: {u_data.get('last_login','Never') or 'Never'}
                        </span>
                    </div>
                """, unsafe_allow_html=True)

                # Reset password section
                with st.expander("🔒 Reset Password", expanded=True):
                    with st.form(f"reset_pw_form_{selected_user}"):
                        new_pw = st.text_input(
                            "New Password",
                            type="password",
                            placeholder="Enter new password for this user"
                        )
                        confirm_pw = st.text_input(
                            "Confirm New Password",
                            type="password",
                            placeholder="Repeat new password"
                        )
                        reset_btn = st.form_submit_button(
                            "🔄 Reset Password",
                            type="primary",
                            use_container_width=True
                        )
                        if reset_btn:
                            if not new_pw or not confirm_pw:
                                st.error("❌ Both password fields are required.")
                            elif new_pw != confirm_pw:
                                st.error("❌ Passwords do not match.")
                            else:
                                ok, msg = auth_system.reset_user_password(
                                    selected_user, new_pw,
                                    performed_by=st.session_state.get("current_user", "manager")
                                )
                                if ok:
                                    st.success(f"✅ {msg}")
                                    st.code(
                                        f"Username : {selected_user}\nNew Password : {new_pw}",
                                        language="text"
                                    )
                                    st.warning("⚠️ Share these updated credentials securely.")
                                else:
                                    st.error(f"❌ {msg}")

                # Toggle active/inactive
                st.markdown("---")
                current_active = u_data.get("is_active", True)
                toggle_label = "🚫 Deactivate Account" if current_active else "✅ Activate Account"
                toggle_help = (
                    "Prevents this user from logging in."
                    if current_active else
                    "Allows this user to log in again."
                )
                if st.button(toggle_label, help=toggle_help, key=f"toggle_{selected_user}"):
                    ok, msg = auth_system.toggle_user_active(
                        selected_user,
                        performed_by=st.session_state.get("current_user", "manager")
                    )
                    if ok:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

    # ── TAB 3 : User List ──────────────────────────────────────────────────
    with tab3:
        st.markdown("### 📋 All Managed Users")

        if not managed_users:
            st.info("No users yet. Create accounts from the **Create User** tab.")
        else:
            # Quick search
            search_term = st.text_input("🔍 Search users", placeholder="Filter by username or email...")
            filtered = {
                u: d for u, d in managed_users.items()
                if search_term.lower() in u.lower() or
                   search_term.lower() in d.get("email", "").lower()
            } if search_term else managed_users

            for uname, udata in filtered.items():
                is_active = udata.get("is_active", True)
                role = udata.get("role", "user")
                last_login = udata.get("last_login") or "Never"
                created = udata.get("created_at", "N/A")

                status_icon = "🟢" if is_active else "🔴"
                role_icon = {"user": "👤", "manager": "👔"}.get(role, "👤")

                with st.expander(
                    f"{status_icon} {role_icon} {uname}  —  {udata.get('email','No email')}",
                    expanded=False
                ):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"""
                            | Field | Value |
                            |---|---|
                            | **Role** | `{role}` |
                            | **Email** | {udata.get('email','N/A')} |
                            | **Status** | {'✅ Active' if is_active else '❌ Inactive'} |
                            | **Created** | {created[:10] if created != 'N/A' else 'N/A'} |
                            | **Last Login** | {last_login[:19] if last_login != 'Never' else 'Never'} |
                        """)
                    with c2:
                        toggle_lbl = "🚫 Deactivate" if is_active else "✅ Activate"
                        if st.button(toggle_lbl, key=f"list_toggle_{uname}", use_container_width=True):
                            ok, msg = auth_system.toggle_user_active(
                                uname,
                                performed_by=st.session_state.get("current_user", "manager")
                            )
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)


# Backward compatibility
class AuthSystem(AdvancedAuthSystem):
    """Legacy compatibility layer"""
    pass


if __name__ == "__main__":
    # Test the advanced auth system
    auth = AdvancedAuthSystem()
    print("Advanced Auth System Test:")
    print("Users:", auth.get_all_users())
    print("Stats:", auth.get_user_stats())