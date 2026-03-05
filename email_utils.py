# import resend
# from config import Config

# resend.api_key = Config.RESEND_API_KEY

# params = {
#     "from": "Test <onboarding@resend.dev>",
#     "to": ["nathanbautista12@gmail.com"], 
#     "subject": "Test from Workout Tracker",
#     "html": "<p>If you're reading this, Resend works!</p>",
# }

# response = resend.Emails.send(params)
# print(response)

from helper_functions import send_verification_email

send_verification_email("nathanbautista12@gmail.com", "test-token-123")