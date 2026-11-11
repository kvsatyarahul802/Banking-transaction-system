# VaultView – Banking Transaction Management and Analysis System

A web-based educational project for managing banking transactions and analysing account activity using Python, Flask, MySQL, Pandas, and NumPy.

## Project Overview

VaultView is an educational banking transaction management and analysis system developed to demonstrate how banking records can be stored, managed, and analysed.

The application allows users to manage accounts, record deposits and withdrawals, view transaction history, and generate useful summaries and visual reports.

> **Note:** This project is an educational simulation. It uses synthetic data and is not a real banking application.

## Key Features

- **User Authentication** – Login-based access to the application.
- **Account Management** – View available customer accounts.
- **Transaction Management** – Record deposits and withdrawals.
- **Money Transfers** – Transfer funds between accounts.
- **Transaction History** – View recorded account transactions.
- **Dashboard** – Display important banking statistics.
- **Financial Reports** – Generate deposit, withdrawal, and balance summaries.
- **Data Visualisation** – Display transaction trends through charts.
- **Transaction Review** – Flag selected transactions for review based on a configurable threshold.
- **Role-Based Login System** – Separate Admin and User accounts with role-based access permissions.
- **Admin Dashboard** – Provides administrative access to system-level operations.
- **User Dashboard** – Allows users to access their associated account information and transactions.


## Technologies Used

| Technology | Purpose |
|---|---|
| HTML, CSS, JavaScript | Frontend development |
| Flask | Backend web framework |
| Python | Application logic |
| MySQL | Database management |
| Pandas | Data analysis |
| NumPy | Numerical operations |
| Chart.js | Dashboard visualisations |

## System Modules

1. **Frontend Module** – Provides the user interface and dashboard.
2. **Backend Module** – Handles application logic and transaction processing.
3. **Database Module** – Stores customer, account, and transaction records.
4. **Analysis Module** – Calculates summaries and analyses transaction data.
5. **Integration and Testing Module** – Connects the application components and checks system functionality.

## Database Structure

The project uses MySQL with the following main tables:

- `customers` – Stores customer information.
- `accounts` – Stores account details.
- `transactions` – Stores deposit and withdrawal records.
- users -stores admin account and users accounts

The database name used by the project is `banking_analysis`.

## Installation and Setup

### Prerequisites

- Python 3.10 or later
- MySQL Server 8.0 or later
- Visual Studio Code (recommended)

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <your-project-folder>
```

### 2. Create the Database

Open MySQL Workbench and execute:

```sql
CREATE DATABASE banking_analysis;
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and update the database configuration with your local MySQL credentials.

Example:

```env
DB_NAME=banking_analysis
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
REVIEW_THRESHOLD=10000
```

Keep your `.env` file private. Never upload database passwords or secret keys to GitHub.

### 4. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Initialise the Database

```bash
python main.py init
python main.py seed
```

These commands create the required tables and insert synthetic sample data.

### 6. Run the Application

```bash
python app.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

## Project Safety and Limitations

- The application is designed for educational purposes only.
- Use synthetic sample data, not real customer or banking information.
- Account balances are simulated using deposits minus withdrawals.
- Transaction review flags indicate records that may need attention; they do not establish fraud.
- The application is not intended for real financial transactions.

## Project Information

| Detail | Information |
|---|---|
| Project Name | VaultView |
| Project Title | Banking Transaction Management and Analysis System |
| Institution | Mohan Babu University |
| Department | Computer Science and Engineering |
| Project Guide | Mohamad Valli |
| Student | B. Heythishwi |

## Team Contributions

This project was developed collaboratively by a team of five members. Each member was responsible for a specific module.

| Team Member | Responsibility | Contribution |
|---|---|---|
| Member 1 | Database Management | Designed MySQL tables, relationships, primary keys, foreign keys, and database constraints. |
| Member 2 | Backend Development | Developed Python database operations and implemented deposit, withdrawal, and transaction processing. |
| Member 3 | Data Analysis | Used Pandas and NumPy to calculate transaction totals, summaries, and monthly trends. |
| Member 4 | Frontend and Visualisation | Developed the user interface and created charts and visual representations of transaction data. |
| **B. Heythishwi (Member 5)** | **Integration and Testing** | **Integrated the frontend, backend, database, and analysis modules. Tested login, account viewing, deposits, withdrawals, transaction history, reports, input validation, data flow, and error handling. Identified issues and verified fixes to ensure the system worked correctly.** |

### My Individual Contribution – B. Heythishwi

My primary responsibility was **Integration and Testing**. My work included:

- Connecting the frontend with the Flask backend.
- Ensuring communication between Python and the MySQL database.
- Integrating transaction and data analysis modules.
- Testing account viewing and transaction operations.
- Checking input validation and error handling.
- Verifying reports and transaction summaries.
- Identifying integration issues and checking their fixes.

Through this work, I helped ensure that all project modules functioned together as a complete application.

## Future Enhancements

- Improved dashboard and reporting features.
- More advanced transaction analysis.
- Enhanced user access controls.
- Additional data visualisation options.
- Improved validation and testing.

## Acknowledgement

We sincerely thank our project guide, **Mohamad Valli**, and **Mohan Babu University** for their guidance and support throughout the development of this project.

---

**VaultView – Turning Banking Transactions into Meaningful Insights.**

## Demo Link

https://banking-transaction-system-2w5r.onrender.com


## Demo Access

VaultView supports two user roles:

- **Admin:** Access to administrative features and system-level management.
- **User:** Access to personal account details and transaction history.

For demonstration access, please contact the project developer.

**Security:** Login credentials and database configuration are not included in this public repository.
