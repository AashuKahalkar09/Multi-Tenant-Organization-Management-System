import bcrypt

class PasswordHasher:
    """Handles password hashing and verification using bcrypt"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a plain text password
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password as string
        """
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)

# Create a singleton instance
password_hasher = PasswordHasher()