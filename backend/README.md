# FinanceTracker / BitFinance Backend
##### Authored by: Abhinav Bichal

The FinanceTracker backend system is composed of a main API which serves the majority of app requests, along with batch processing scripts that run periodically + asynchronously to properly update and manage user financial data & app data.

### The API
The FinanceTracker backend API works closely with Plaid services to retrieve user financial data. This API is the main driver for handling user logins, retrieving data from Plaid, populating the database with user data, and returning it back to the user.

Due to the many complex tasks of the API and requirements for data privacy & security, the API has the following major tasks:

- Collect and populate user data efficiently on every Plaid Link Account action
- Encrypt both the storage and transmission of user financial data for all sensitive data
- Act as the intermediary communication layer between the database and application

### The Other Stuff
The rest of the backend is flexible to work with any other technology and infrastructure, as long as the main goals of managing user data and application lifecycle events are properly implemented.

Currently, these are the planned batch processing scripts that are necessary for the backend system to work properly:

- Periodically update user transaction & stock data by communicating with the database and the Plaid API
- Manage any backend infrastructure details such as data replication, server active sessions, etc.


### ⚠️ Issues & Current Progress
As of right now, the basic functionality of setting up the Plaid Link and gathering user data is implemented on the API. The batch scripts are still in progress. Everything is Dockerized, and we are in the debugging stage for ensuring containers are consistent.


There is a lot left to do and future plans that require us to change critical elements of the architecture, but most changes should be reflected in this document whenever they occur.
