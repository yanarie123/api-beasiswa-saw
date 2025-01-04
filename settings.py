# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'  # Your Gmail
EMAIL_HOST_PASSWORD = 'your-app-password'  # Your Gmail App Password
DEFAULT_FROM_EMAIL = 'your-email@gmail.com'

# Frontend URL for password reset
FRONTEND_URL = 'http://localhost:3000'  # Your frontend URL 