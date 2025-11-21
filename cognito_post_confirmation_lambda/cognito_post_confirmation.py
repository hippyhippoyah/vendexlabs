import logging
from peewee import IntegrityError
from config import db
from models import User, VendorList

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    Cognito Post-Confirmation trigger handler.
    Creates a User record and default personal vendor list when a user confirms their account.
    """
    try:
        # Extract email from Cognito event
        user_attributes = event.get('request', {}).get('userAttributes', {})
        email = user_attributes.get('email')
        
        if not email:
            logger.warning("No email found in Cognito event, skipping user creation")
            # Return event to allow signup to proceed
            return event
        
        logger.info(f"Processing post-confirmation for user: {email}")
        
        # Connect to database
        db.connect(reuse_if_open=True)
        
        try:
            # Use a transaction to make operations atomic and prevent race conditions
            with db.atomic():
                # Create User record (idempotent - won't fail if user already exists)
                user, user_created = User.get_or_create(
                    email=email,
                    defaults={'name': None}
                )
                
                if user_created:
                    logger.info(f"Created new user record for: {email}")
                else:
                    logger.info(f"User already exists: {email}")
                
                # Check if vendor list already exists first to avoid race condition
                # This is more reliable than get_or_create for concurrent requests
                try:
                    vendor_list = VendorList.get(
                        VendorList.user == user,
                        VendorList.name == 'master-list',
                        VendorList.account.is_null()
                    )
                    logger.info(f"Default vendor list 'master-list' already exists for user: {email}")
                except VendorList.DoesNotExist:
                    # Create default personal vendor list only if it doesn't exist
                    try:
                        vendor_list = VendorList.create(
                            user=user,
                            name='master-list',
                            account=None
                        )
                        logger.info(f"Created default vendor list 'master-list' for user: {email}")
                    except IntegrityError:
                        # Race condition: another process created it between our check and create
                        # Fetch the existing one
                        vendor_list = VendorList.get(
                            VendorList.user == user,
                            VendorList.name == 'master-list',
                            VendorList.account.is_null()
                        )
                        logger.info(f"Vendor list was created by another process, using existing one for user: {email}")
            
        except IntegrityError as e:
            logger.error(f"Database integrity error for user {email}: {str(e)}")
            db.rollback()
        except Exception as e:
            logger.error(f"Error creating user/vendor list for {email}: {str(e)}")
            db.rollback()
        finally:
            db.close()
        
        # Always return the event to allow Cognito signup to proceed
        # Even if there's an error, we don't want to block user signup
        return event
        
    except Exception as e:
        logger.error(f"Unexpected error in post-confirmation handler: {str(e)}")
        # Return event to allow signup to proceed even on unexpected errors
        return event

