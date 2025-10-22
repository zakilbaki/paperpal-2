import streamlit as st
from crud import insert_sample, find_all, delete_all

st.title("💽 MongoDB Quick Dashboard")

# Insert
st.header("Add a New Message")
name = st.text_input("Name")
msg = st.text_area("Message")

if st.button("Insert Document"):
    if name and msg:
        _id = insert_sample({"name": name, "msg": msg})
        st.success(f"✅ Inserted with ID: {_id}")
    else:
        st.error("Please fill in both fields.")

# View all
st.header("All Documents in Database")
docs = find_all()
st.json(docs)

# Delete all
if st.button("Delete All Documents"):
    st.warning(delete_all())
