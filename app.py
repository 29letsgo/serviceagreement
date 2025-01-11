import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# Define a secure password
PASSWORD = "Larkin"  # Replace with your desired password

# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Password Protection Logic
if not st.session_state.authenticated:
    st.title("Service Agreement Management System")
    password = st.text_input("Enter the password:", type="password")

    if password == PASSWORD:
        st.session_state.authenticated = True
        st.experimental_set_query_params(authenticated="true")  # Mark session as authenticated
        st.success("Access granted! Reloading the app...")
    elif password:
        st.error("Incorrect password. Please try again.")
    st.stop()  # Stop the app until the correct password is entered
else:
    # Main App Content
    st.title("Service Agreement Management System")
    st.success("Welcome back!")

    # Your actual app logic begins here
    st.write("This is your main app content!")
    # Add all your app features below

# Database connection
def get_db_connection():
    return sqlite3.connect("database.db")

# Initialize the database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create agreements table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agreements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property TEXT NOT NULL,
            service_type TEXT NOT NULL,
            vendor TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            price REAL NOT NULL,
            increase_percent REAL NOT NULL,
            status TEXT NOT NULL
        )
    """)

    # Create properties table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    # Create emails table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE
        )
    """)

    conn.commit()
    conn.close()

# Load data from agreements
def load_agreements(status_filter=None):
    conn = get_db_connection()
    query = "SELECT * FROM agreements"
    if status_filter:
        query += f" WHERE status = '{status_filter}'"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Load data from properties
def load_properties():
    conn = get_db_connection()
    properties = pd.read_sql_query("SELECT * FROM properties", conn)
    conn.close()
    return properties

# Load data from emails
def load_emails():
    conn = get_db_connection()
    emails = pd.read_sql_query("SELECT * FROM emails", conn)
    conn.close()
    return emails

# Add a new property
def add_property(name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO properties (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

# Add new agreement
def add_agreement(property, service_type, vendor, start_date, end_date, price, increase_percent, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO agreements (property, service_type, vendor, start_date, end_date, price, increase_percent, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(query, (property, service_type, vendor, start_date, end_date, price, increase_percent, status))
    conn.commit()
    conn.close()

# Update an agreement
def update_agreement(agreement_id, **kwargs):
    conn = get_db_connection()
    cursor = conn.cursor()
    update_fields = ", ".join(f"{key} = ?" for key in kwargs.keys())
    query = f"UPDATE agreements SET {update_fields} WHERE id = ?"
    cursor.execute(query, list(kwargs.values()) + [agreement_id])
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Streamlit App
st.title("Service Agreement Management System")

# Navigation tabs
tab = st.sidebar.radio("Menu", ["Dashboard", "Dashboard Edit", "View Agreements", "Add Agreement", "Edit/Archive Agreement", "Archived Agreements", "Manage Email List"])

# Dashboard
if tab == "Dashboard":
    st.header("Summary Dashboard")
    data = load_agreements()

    if data.empty:
        st.write("No agreements available to display. Add new agreements to populate the dashboard.")
    else:
        properties = load_properties()
        property_names = ["All Properties"] + properties["name"].tolist()

        # Property filter dropdown
        selected_property = st.selectbox("Filter by Property", property_names)

        if selected_property != "All Properties":
            data = data[data["property"] == selected_property]

        # Filter out archived agreements
        active_data = data[data["status"] != "Archived"]

        # Summary metrics
        total_agreements = len(active_data)
        active_agreements = len(active_data[active_data["status"] == "Active"])
        avg_increase = active_data["increase_percent"].mean()

        st.metric("Total Agreements", total_agreements)
        st.metric("Active Agreements", active_agreements)
        st.metric("Average Annual Increase (%)", f"{avg_increase:.2f}" if not pd.isnull(avg_increase) else "N/A")

        # Display active agreements table
        st.subheader("All Active Agreements")
        st.dataframe(active_data)

        # Visualize data with a graph
        st.subheader("Price Distribution by Service Type")
        fig = px.bar(
            active_data,
            x="service_type",
            y="price",
            color="status",
            title="Price Distribution by Service Type",
            labels={"service_type": "Service Type", "price": "Price ($)"},
        )
        st.plotly_chart(fig, use_container_width=True)

# Dashboard Edit
elif tab == "Dashboard Edit":
    st.header("Manage Properties for Dashboard")
    properties = load_properties()

    # Display current properties
    st.subheader("Current Properties")
    if not properties.empty:
        st.dataframe(properties)
    else:
        st.write("No properties found. Add properties below.")

    # Add new property
    new_property = st.text_input("Add New Property")
    if st.button("Add Property"):
        try:
            add_property(new_property)
            st.success(f"Property '{new_property}' added successfully!")
        except sqlite3.IntegrityError:
            st.error(f"Property '{new_property}' already exists!")

# View Agreements
elif tab == "View Agreements":
    st.header("View All Active Agreements")
    data = load_agreements(status_filter="Active")

    if not data.empty:
        st.subheader("All Active Agreements")
        st.dataframe(data)

        # Upcoming Renewals
        st.subheader("Upcoming Renewals (Next 30 Days)")
        today = datetime.today()
        upcoming_renewals = data[pd.to_datetime(data["end_date"]) <= (today + timedelta(days=30))]

        if not upcoming_renewals.empty:
            st.dataframe(upcoming_renewals)
        else:
            st.write("No agreements expiring in the next 30 days.")
    else:
        st.write("No active agreements found.")

# Add Agreement
elif tab == "Add Agreement":
    st.header("Add New Service Agreement")
    properties = load_properties()

    if properties.empty:
        st.warning("No properties found. Please add properties in the 'Dashboard Edit' tab first.")
    else:
        property = st.selectbox("Property Name", properties["name"])
        service_type = st.text_input("Service Type")
        vendor = st.text_input("Vendor")
        start_date = st.date_input("Start Date", datetime.today())
        end_date = st.date_input("End Date", datetime.today())
        price = st.number_input("Price", min_value=0.0, step=0.01)
        increase_percent = st.number_input("Annual Increase (%)", min_value=0.0, step=0.1)
        status = st.selectbox("Status", ["Active", "Completed", "Archived"])

        if st.button("Add Agreement"):
            add_agreement(property, service_type, vendor, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"),
                          price, increase_percent, status)
            st.success("Service Agreement added successfully!")

# Edit/Archive Agreement
elif tab == "Edit/Archive Agreement":
    st.header("Edit or Archive Service Agreement")
    data = load_agreements()

    if not data.empty:
        agreement_id = st.selectbox("Select Agreement to Edit", data["id"].tolist())
        selected_agreement = data[data["id"] == agreement_id].iloc[0]

        property = st.text_input("Property Name", value=selected_agreement["property"])
        service_type = st.text_input("Service Type", value=selected_agreement["service_type"])
        vendor = st.text_input("Vendor", value=selected_agreement["vendor"])
        start_date = st.date_input("Start Date", value=datetime.strptime(selected_agreement["start_date"], "%Y-%m-%d"))
        end_date = st.date_input("End Date", value=datetime.strptime(selected_agreement["end_date"], "%Y-%m-%d"))
        price = st.number_input("Price", min_value=0.0, step=0.01, value=selected_agreement["price"])
        increase_percent = st.number_input("Annual Increase (%)", min_value=0.0, step=0.1, value=selected_agreement["increase_percent"])
        status = st.selectbox("Status", ["Active", "Completed", "Archived"], index=["Active", "Completed", "Archived"].index(selected_agreement["status"]))

        if st.button("Update Agreement"):
            update_agreement(agreement_id, property=property, service_type=service_type, vendor=vendor,
                             start_date=start_date.strftime("%Y-%m-%d"), end_date=end_date.strftime("%Y-%m-%d"),
                             price=price, increase_percent=increase_percent, status=status)
            st.success("Service Agreement updated successfully!")

        if st.button("Archive Agreement"):
            update_agreement(agreement_id, status="Archived")
            st.success("Agreement archived successfully!")
    else:
        st.write("No agreements available to edit or archive.")

# Archived Agreements
elif tab == "Archived Agreements":
    st.header("View All Archived Agreements")
    data = load_agreements(status_filter="Archived")

    if not data.empty:
        st.dataframe(data)
    else:
        st.write("No archived agreements found.")

# Manage Email List
elif tab == "Manage Email List":
    st.header("Manage Catch-All Email List")
    st.write("This email list is used to send reminders for upcoming expiring service agreements.")
    emails = load_emails()

    # Display current emails
    st.subheader("Current Emails")
    if not emails.empty:
        st.dataframe(emails)
    else:
        st.write("No emails found. Add a new one below.")

    # Add new email
    new_email = st.text_input("Add New Email")
    if st.button("Add Email"):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO emails (email) VALUES (?)", (new_email,))
            conn.commit()
            conn.close()
            st.success(f"Email '{new_email}' added successfully!")
        except sqlite3.IntegrityError:
            st.error(f"Email '{new_email}' already exists!")

    # Send email reminders
    st.subheader("Send Email Reminders for Upcoming Renewals")
    if st.button("Send Email Reminders"):
        data = load_agreements(status_filter="Active")
        today = datetime.today()
        upcoming_renewals = data[pd.to_datetime(data["end_date"]) <= (today + timedelta(days=30))]

        if not upcoming_renewals.empty:
            if not emails.empty:
                for _, email_row in emails.iterrows():
                    for _, agreement in upcoming_renewals.iterrows():
                        # Replace with your actual email-sending function
                        # Here, you can call send_email_reminder function if already implemented
                        print(f"Sending email to {email_row['email']} for {agreement['service_type']} expiring on {agreement['end_date']}")
                st.success("Email reminders sent successfully!")
            else:
                st.warning("No emails found in the catch-all email list.")
        else:
            st.warning("No upcoming renewals found to send reminders for.")


