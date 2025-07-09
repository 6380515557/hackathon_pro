# backend/routers/notifications.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from bson import ObjectId # For validating ObjectIds in path parameters
from datetime import datetime # Import datetime for timestamp

from ..database import get_database # Correctly import get_database
from ..schemas import NotificationCreate, NotificationResponse, NotificationSeverity, UserResponse
# Assuming get_current_active_user and role_required are in ..auth.router or ..auth.security
# Based on your previous code, they are likely in ..auth.router
from ..auth.router import get_current_user, role_required # Reverted to get_current_user and role_required as per previous working code

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# Helper function to convert MongoDB document to NotificationResponse
def notification_doc_to_response(doc: dict) -> NotificationResponse:
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return NotificationResponse(**doc)

# --- Helper Function for Internal Use (e.g., from other parts of your app) ---
# This helper function will now also take 'db' as an argument
async def create_notification_helper(
    db, # Pass the database instance
    message: str,
    severity: NotificationSeverity = NotificationSeverity.INFO,
    user_id: Optional[str] = None, # MongoDB ObjectId as string
    username: Optional[str] = None # Optional username to display
):
    """
    Helper function to create and store a notification.
    Can be called from other parts of the application (e.g., a service layer).
    """
    notifications_collection = db["notifications"] # Access collection via db
    
    notification_data = {
        "message": message,
        "severity": severity.value, # Store enum value
        "read": False,
        "timestamp": datetime.utcnow()
    }
    
    if user_id:
        try:
            notification_data["user_id"] = ObjectId(user_id) # Store as ObjectId
        except Exception:
            print(f"Invalid user_id format for notification: {user_id}")
            # Decide how to handle: skip user_id, raise error, or log
            del notification_data["user_id"] # Remove invalid user_id
    if username:
        notification_data["username"] = username

    try:
        result = await notifications_collection.insert_one(notification_data)
        created_notification = await notifications_collection.find_one({"_id": result.inserted_id})
        if created_notification:
            return notification_doc_to_response(created_notification)
        return None
    except Exception as e:
        print(f"Error creating notification: {e}")
        return None

# --- API Endpoints ---

@router.post("/create", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_new_notification_api(
    notification_in: NotificationCreate,
    current_user: UserResponse = Depends(role_required(["admin"])), # Only admins can create general notifications via API
    db = Depends(get_database) # Use get_database dependency
):
    """
    API endpoint to create a new notification.
    Requires 'admin' role. Can specify user_id/username for target.
    """
    notifications_collection = db["notifications"] # Access collection via db
    users_collection = db["users"] # Access users collection via db

    # If user_id is provided, convert it to ObjectId for storage
    if notification_in.user_id:
        try:
            notification_in.user_id = str(ObjectId(notification_in.user_id)) # Convert to ObjectId then back to string for Pydantic
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id format")
            
        # Optionally, fetch username if only user_id is provided
        if not notification_in.username:
            target_user = await users_collection.find_one({"_id": ObjectId(notification_in.user_id)})
            if target_user:
                notification_in.username = target_user.get("username")

    notification_data = notification_in.model_dump(by_alias=True, exclude_unset=True)
    notification_data["timestamp"] = datetime.utcnow() # Ensure timestamp is current UTC
    notification_data["read"] = False # Ensure new notifications are unread

    # Convert user_id to ObjectId for storage in MongoDB
    if notification_data.get("user_id"):
        notification_data["user_id"] = ObjectId(notification_data["user_id"])

    result = await notifications_collection.insert_one(notification_data)
    created_notification = await notifications_collection.find_one({"_id": result.inserted_id})
    if created_notification:
        return notification_doc_to_response(created_notification)
    raise HTTPException(status_code=500, detail="Failed to create notification")


@router.get("/me", response_model=List[NotificationResponse])
async def get_my_notifications(
    current_user: UserResponse = Depends(get_current_user), # Use get_current_user as per previous working code
    db = Depends(get_database), # Use get_database dependency
    read: Optional[bool] = False, # Default to False to get unread by default if not specified
    severity: Optional[NotificationSeverity] = None
):
    """
    Retrieves notifications for the current authenticated user.
    Optionally filters for read status and severity.
    """
    notifications_collection = db["notifications"] # Access collection via db
    
    # Query for notifications specific to the current user's ID or global notifications (user_id: None)
    query = {"$or": [{"user_id": ObjectId(current_user.id)}, {"user_id": None}]}
    
    if read is not None: # Check if read filter is explicitly provided
        query["read"] = read
    if severity:
        query["severity"] = severity.value # Use .value for enum
        
    notifications_cursor = notifications_collection.find(query).sort("timestamp", -1) # Sort by most recent first
    my_notifications = await notifications_cursor.to_list(length=None) # Fetch all

    if not my_notifications:
        return []

    return [notification_doc_to_response(n) for n in my_notifications]


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: str,
    current_user: UserResponse = Depends(get_current_user), # Use get_current_user
    db = Depends(get_database) # Use get_database dependency
):
    """
    Marks a specific notification as read for the current user.
    Users can mark their own; admins/supervisors can mark any.
    """
    notifications_collection = db["notifications"] # Access collection via db

    if not ObjectId.is_valid(notification_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification ID format")

    notification_obj_id = ObjectId(notification_id)
    
    notification_doc = await notifications_collection.find_one({"_id": notification_obj_id})
    if not notification_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    # Authorization: Admin/Supervisor can update any, regular user can only update their own
    # Assuming roles are 'admin', 'supervisor', 'operator', 'viewer'
    if not any(role in current_user.roles for role in ["admin", "supervisor"]): # Check if current user has admin/supervisor role
        # If not admin/supervisor, check if the notification belongs to the current user
        # Notification can be global (user_id is None) or specific to a user
        is_global_notification = notification_doc.get("user_id") is None
        is_my_notification = (
            notification_doc.get("user_id") == ObjectId(current_user.id)
            or notification_doc.get("username") == current_user.username
        )
        if not (is_global_notification or is_my_notification):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to mark this notification as read")
    
    result = await notifications_collection.update_one(
        {"_id": notification_obj_id},
        {"$set": {"read": True}}
    )

    if result.matched_count == 0:
        # It could be 0 if already read, or if not found (though checked above)
        updated_notification = await notifications_collection.find_one({"_id": notification_obj_id})
        if updated_notification:
            return notification_doc_to_response(updated_notification) # Return current state
        raise HTTPException(status_code=500, detail="Failed to update notification or notification not found after update attempt.")

    updated_notification = await notifications_collection.find_one({"_id": notification_obj_id})
    if updated_notification:
        return notification_doc_to_response(updated_notification)
    raise HTTPException(status_code=500, detail="Notification updated but could not be retrieved.")

@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    current_user: UserResponse = Depends(role_required(["admin", "supervisor"])), # Admins/supervisors can delete
    db = Depends(get_database) # Use get_database dependency
):
    """
    Deletes a specific notification. Requires 'admin' or 'supervisor' role.
    """
    notifications_collection = db["notifications"] # Access collection via db

    if not ObjectId.is_valid(notification_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification ID format")

    result = await notifications_collection.delete_one({"_id": ObjectId(notification_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return {} # 204 No Content response
