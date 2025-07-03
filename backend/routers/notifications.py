# backend/routers/notifications.py

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId
from typing import List, Optional

# Import schemas
from ..schemas import NotificationCreate, NotificationResponse, UserResponse, NotificationSeverity

# Import database collection and security dependencies
from ..database import notifications_collection, users_collection # Need users_collection for fetching user details
from ..auth.security import get_current_active_user, role_required

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)

# Dependency to get the notifications collection
async def get_notifications_collection() -> AsyncIOMotorCollection:
    """Dependency function to provide the notifications collection."""
    return notifications_collection

# --- Helper Function for Internal Use (e.g., from other parts of your app) ---
async def create_notification(
    message: str,
    severity: NotificationSeverity = NotificationSeverity.INFO,
    user_id: Optional[str] = None, # MongoDB ObjectId as string
    username: Optional[str] = None # Optional username to display
):
    """
    Helper function to create and store a notification.
    Can be called from other parts of the application (e.g., a service layer).
    """
    notification_data = {
        "message": message,
        "severity": severity,
        "read": False,
        "timestamp": datetime.utcnow()
    }
    
    if user_id:
        notification_data["user_id"] = ObjectId(user_id) # Store as ObjectId
    if username:
        notification_data["username"] = username

    try:
        result = await notifications_collection.insert_one(notification_data)
        # Optionally, retrieve and return the created notification
        created_notification = await notifications_collection.find_one({"_id": result.inserted_id})
        if created_notification:
            created_notification["id"] = str(created_notification.pop("_id"))
            return NotificationResponse(**created_notification)
        return None
    except Exception as e:
        print(f"Error creating notification: {e}")
        return None

# --- API Endpoints ---

@router.post("/create", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_new_notification_api(
    notification_in: NotificationCreate,
    current_user: UserResponse = Depends(role_required(["admin"])), # Only admins can create general notifications via API
    collection: AsyncIOMotorCollection = Depends(get_notifications_collection)
):
    """
    API endpoint to create a new notification.
    Requires 'admin' role. Can specify user_id/username for target.
    """
    # If user_id is provided, convert it to ObjectId for storage
    if notification_in.user_id:
        try:
            notification_in.user_id = ObjectId(notification_in.user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id format")
            
        # Optionally, fetch username if only user_id is provided
        if not notification_in.username:
            target_user = await users_collection.find_one({"_id": notification_in.user_id})
            if target_user:
                notification_in.username = target_user.get("username")

    notification_data = notification_in.model_dump(by_alias=True, exclude_unset=True)
    notification_data["timestamp"] = datetime.utcnow() # Ensure timestamp is current UTC
    notification_data["read"] = False # Ensure new notifications are unread

    result = await collection.insert_one(notification_data)
    created_notification = await collection.find_one({"_id": result.inserted_id})
    if created_notification:
        created_notification["id"] = str(created_notification.pop("_id"))
        return NotificationResponse(**created_notification)
    raise HTTPException(status_code=500, detail="Failed to create notification")


@router.get("/me", response_model=List[NotificationResponse])
async def get_my_notifications(
    current_user: UserResponse = Depends(get_current_active_user),
    collection: AsyncIOMotorCollection = Depends(get_notifications_collection),
    unread_only: bool = False
):
    """
    Retrieves notifications for the current authenticated user.
    Optionally filters for unread notifications.
    """
    query = {"$or": [{"user_id": ObjectId(current_user.id)}, {"user_id": None}]} # Specific user or global
    if unread_only:
        query["read"] = False
        
    notifications_cursor = collection.find(query).sort("timestamp", -1) # Sort by most recent first
    my_notifications = await notifications_cursor.to_list(length=None) # Fetch all

    if not my_notifications:
        return []

    return [NotificationResponse(**{**n, "id": str(n["_id"])}) for n in my_notifications]


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    collection: AsyncIOMotorCollection = Depends(get_notifications_collection)
):
    """
    Marks a specific notification as read for the current user.
    """
    try:
        oid = ObjectId(notification_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification ID format")

    # Ensure the user has access to this notification (either owns it or it's global)
    notification = await collection.find_one({"_id": oid})
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    
    if notification.get("user_id") and str(notification["user_id"]) != current_user.id:
        if current_user.role not in ["admin"]: # Admins can mark others' notifications as read
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to mark this notification as read")
    
    update_result = await collection.update_one(
        {"_id": oid},
        {"$set": {"read": True}}
    )

    if update_result.modified_count == 0:
        # It could be 0 if already read, or if not found (though checked above)
        updated_notification = await collection.find_one({"_id": oid})
        if updated_notification:
             updated_notification["id"] = str(updated_notification.pop("_id"))
             return NotificationResponse(**updated_notification) # Return current state
        raise HTTPException(status_code=500, detail="Failed to update notification or notification not found after update attempt.")

    updated_notification = await collection.find_one({"_id": oid})
    if updated_notification:
        updated_notification["id"] = str(updated_notification.pop("_id"))
        return NotificationResponse(**updated_notification)
    raise HTTPException(status_code=500, detail="Notification updated but could not be retrieved.")

@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    current_user: UserResponse = Depends(role_required(["admin"])), # Only admins can delete notifications via API
    collection: AsyncIOMotorCollection = Depends(get_notifications_collection)
):
    """
    Deletes a specific notification. Requires 'admin' role.
    """
    try:
        oid = ObjectId(notification_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification ID format")

    delete_result = await collection.delete_one({"_id": oid})

    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return