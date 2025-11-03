import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

def get_headers(token_type="access"):
    token = st.session_state.access_token if token_type == "access" else st.session_state.refresh_token
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

st.set_page_config(page_title="💸 Expense Splitter", layout="wide")
st.title("💸 Group Expense Splitter (FastAPI + Streamlit)")

tabs = st.tabs(["Register", "Login", "Groups", "Payments"])


with tabs[0]:
    st.subheader("Register")
    with st.form("register_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["user", "admin"])
        submit = st.form_submit_button("Register")
    if submit:
        res = requests.post(f"{API_URL}/register", data={"username": username, "password": password, "role": role})
        st.json(res.json())

with tabs[1]:
    st.subheader("Login")
    with st.form("login_form"):
        username = st.text_input("Login Username")
        password = st.text_input("Login Password", type="password")
        submit = st.form_submit_button("Login")
    if submit:
        res = requests.post(f"{API_URL}/login", data={"username": username, "password": password})
        if res.status_code == 200:
            tokens = res.json()
            st.session_state.access_token = tokens["access_token"]
            st.session_state.refresh_token = tokens["refresh_token"]
            st.success("Logged in successfully")
        else:
            st.error(res.json())


with tabs[2]:
    st.subheader("Groups")
    with st.expander("Create Group"):
        with st.form("create_group_form"):
            group_name = st.text_input("Group Name")
            budget = st.number_input("Budget", min_value=0.0)
            add_creator = st.checkbox("Add Creator", value=True)
            submit = st.form_submit_button("Create")
        if submit:
            res = requests.post(f"{API_URL}/groups/create", data={"group_name": group_name, "budget": budget, "add_creator": str(add_creator).lower()}, headers=get_headers())
            st.json(res.json())

    with st.expander("Add User to Group"):
        with st.form("add_user"):
            username = st.text_input("Username to Add")
            group_name = st.text_input("Group Name")
            submit = st.form_submit_button("Add User")
        if submit:
            res = requests.post(f"{API_URL}/groups/add-user", data={"username": username, "group_name": group_name}, headers=get_headers())
            st.json(res.json())

    if st.button("List All Groups"):
        res = requests.get(f"{API_URL}/groups", headers=get_headers())
        st.json(res.json())


with tabs[3]:
    st.subheader("Payments")
    with st.expander("Pay Your Share"):
        with st.form("pay_form"):
            group_name = st.text_input("Group Name (Pay)")
            amount = st.number_input("Amount to Pay", min_value=0.0)
            submit = st.form_submit_button("Submit Payment")
        if submit:
            res = requests.post(f"{API_URL}/groups/{group_name}/pay", data={"amount": amount}, headers=get_headers())
            st.json(res.json())

    with st.expander("Approve Payments (Admin Only)"):
        with st.form("approve_form"):
            group_name = st.text_input("Group Name (Approve)")
            username = st.text_input("Username to Approve/Deny")
            action = st.selectbox("Action", ["approve", "deny"])
            submit = st.form_submit_button("Submit")
        if submit:
            res = requests.post(f"{API_URL}/groups/{group_name}/approve", data={"username": username, "action": action}, headers=get_headers())
            st.json(res.json())

    with st.expander("View Group Status"):
        group_name = st.text_input("Group Name (Status)")
        if st.button("Check Status"):
            res = requests.get(f"{API_URL}/groups/{group_name}/status", headers=get_headers())
            st.json(res.json())