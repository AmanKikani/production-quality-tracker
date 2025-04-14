# Production & Quality Tracker

A comprehensive web application for real-time production monitoring and quality tracking, inspired by OffSight's production tracking solution for the offsite construction, modular, and prefab industry.

## Features

### 1. Real-Time Production Monitoring
- Interactive dashboard with project progress visualization
- Module status tracking and updates
- Timeline adherence tracking

### 2. Quality Issue Management
- Real-time issue flagging and tracking
- Severity and category classification
- Resolution workflow

### 3. Task Management System
- Task assignment and tracking
- Due date monitoring
- Task completion workflow

### 4. Data Analytics and Reporting
- Project completion analytics
- Quality issue statistics
- Task performance metrics
- User productivity reports

### 5. Notification System
- Real-time alerts for new issues
- Task assignment notifications
- Overdue task alerts
- Resolution confirmations

## Technical Stack

- **Frontend & Backend**: Streamlit (Python)
- **Data Storage**: CSV files (for MVP demonstration)
- **Visualization**: Plotly, Matplotlib
- **User Authentication**: Session-based authentication

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/production-quality-tracker.git
cd production-quality-tracker
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
streamlit run app.py
```

2. Access the application in your browser at http://localhost:8501

3. Log in using one of the demo accounts:
   - Operator: username=`john_doe`, password=`password123`
   - Inspector: username=`jane_smith`, password=`pass456`
   - Manager: username=`mike_jones`, password=`secure789`

## Project Structure

- `app.py`: Main application entry point
- `pages/`: Individual page modules
  - `projects.py`: Project management page
  - `issues.py`: Quality issues management page
  - `tasks.py`: Task management page
  - `reports.py`: Analytics and reporting page
- `utils/`: Utility modules
  - `auth.py`: Authentication functions
  - `database.py`: Data access functions
  - `notifications.py`: Notification system
  - `helpers.py`: UI and helper functions
- `data/`: Sample data files
  - `users.csv`: User information
  - `projects.csv`: Project data
  - `modules.csv`: Module data
  - `issues.csv`: Quality issues data
  - `tasks.csv`: Task assignments data

## Future Enhancements

1. Database Integration: Replace CSV storage with a proper database system
2. API Development: Create a RESTful API for mobile app integration
3. File Uploads: Allow attachment of photos and documents to issues and tasks
4. Advanced Analytics: Predictive analytics for issue prevention
5. Mobile App: Native mobile application for field use

## License

This project is licensed under the MIT License - see the LICENSE file for details. 