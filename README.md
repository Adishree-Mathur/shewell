# Shewell - Healthcare Management Platform

A comprehensive web-based healthcare management platform that connects patients with doctors, provides mental health resources, and offers personalized health tracking features.

## Features

- **Doctor Appointment Booking**: Schedule and manage appointments with healthcare professionals
- **Doctor Dashboard**: Manage patient appointments and medical records
- **Patient Dashboard**: Track health metrics, appointments, and medical history
- **Mental Health Resources**: Access mental health support and counseling information
- **Health Tracking**: Monitor menstrual cycles and other health metrics
- **Chatbot Support**: AI-powered chatbot for health-related queries
- **Media Content**: Reels and educational content about health topics
- **User Authentication**: Secure login and registration system

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: Supabase PostgreSQL via the Supabase Python client
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: Heroku or any platform that supports environment variables

## Database Options

This app now uses Supabase directly for all data access.

Required environment variables:

- `SUPABASE_URL`
- `SUPABASE_KEY`

The app expects these Supabase tables to exist: `user`, `doctor`, `appointment`, and `chat_history`.
The exact SQL is available in [supabase_schema.sql](supabase_schema.sql).

## Project Structure

```
shewell/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Procfile              # Heroku deployment configuration
├── static/               # Static files
│   ├── css/             # Stylesheets
│   ├── images/          # Image assets
│   └── js/              # JavaScript files
└── templates/           # HTML templates
    ├── base.html        # Base template
    ├── index.html       # Home page
    ├── login.html       # Login page
    ├── register.html    # Registration page
    ├── doctors.html     # Doctors list
    ├── book_appointment.html
    ├── doctor_dashboard.html
    ├── patient_dashboard.html
    ├── mental_health.html
    ├── periods.html
    ├── chatbot.html
    ├── reels.html
    └── about.html       # About page
```

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/Adishree-Mathur/shewell.git
   cd shewell
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Supabase**
   Set `SUPABASE_URL` and `SUPABASE_KEY` in `.env`, then create the required tables in your Supabase project.

5. **Run the application**
   ```bash
   python app.py
   ```

The application will be available at `http://localhost:5000`

## Database Migrations

This project no longer uses Alembic migrations. Database changes should be made in Supabase.

## Usage

### For Patients
1. Register or login to your account
2. View available doctors and book appointments
3. Access your dashboard to track health metrics
4. Use the chatbot for health-related questions
5. Explore mental health resources

### For Doctors
1. Login to your doctor account
2. Access your dashboard to view appointments
3. Manage patient records
4. Update availability and other profile information

## Deployment

This application is configured for Heroku deployment. The `Procfile` contains the deployment configuration.

To deploy to Heroku:
```bash
heroku create your-app-name
git push heroku main
```

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is open source and available under the MIT License.

## Author

**Adishree-Mathur**
- GitHub: [Adishree-Mathur](https://github.com/Adishree-Mathur)

## Support

For issues, questions, or suggestions, please open an issue on the [GitHub repository](https://github.com/Adishree-Mathur/shewell).

## Live Demo

You can access the live version of SheWell here:

[SheWell Live Demo](https://shewell-n3v6.onrender.com/)
