from pymongo import MongoClient, ASCENDING
from pymongo.database import Database
from app.config import settings
from typing import Optional


class DatabaseManager:
    """Manages MongoDB connections and operations"""
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.master_db: Optional[Database] = None
    
    def connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(settings.MONGODB_URL)
            self.master_db = self.client[settings.MASTER_DB_NAME]
            
            # Create indexes for better performance
            self.master_db.organizations.create_index(
                [("organization_name", ASCENDING)], 
                unique=True
            )
            self.master_db.admins.create_index(
                [("email", ASCENDING)], 
                unique=True
            )
            
            print(f"✅ Connected to MongoDB: {settings.MASTER_DB_NAME}")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client is not None:
            self.client.close()
            print("✅ Disconnected from MongoDB")
    
    def get_master_db(self) -> Database:
        """Get master database instance"""
        if self.master_db is None:
            raise Exception("Database not connected")
        return self.master_db
    
    def get_org_collection(self, collection_name: str):
        """Get organization-specific collection"""
        if self.master_db is None:
            raise Exception("Database not connected")
        return self.master_db[collection_name]
    
    def create_org_collection(self, collection_name: str):
        """Create a new organization collection"""
        if self.master_db is None:
            raise Exception("Database not connected")
        
        # MongoDB creates collection automatically on first insert
        # But we can explicitly create it with validation
        collection = self.master_db[collection_name]
        
        # Create a sample index (you can customize based on needs)
        collection.create_index([("created_at", ASCENDING)])
        
        return collection
    
    def drop_org_collection(self, collection_name: str):
        """Drop an organization collection"""
        if self.master_db is None:
            raise Exception("Database not connected")
        
        self.master_db[collection_name].drop()


# Global database manager instance
db_manager = DatabaseManager()
