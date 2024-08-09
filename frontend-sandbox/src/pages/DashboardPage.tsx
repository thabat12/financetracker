import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import { Link, Outlet } from "react-router-dom";
import SummaryPage from "./SummaryPage";
import TransactionsPage from "./TransactionsPage";
import SettingsPage from "./SettingsPage";

function DashboardPage() {
    return (
        <div>

            <div className="flex flex-col h-full">
                <h2>Fintracker Dashboard</h2>

                <Link to="/dashboard/summary">summary</Link>
                <Link to="/dashboard/transactions">transactions</Link>
                <Link to="/dashboard/settings">settings</Link>
            </div>

            <div>

                {/* <Routes>
                    <Route path="/dashboard/summary" element={<SummaryPage/>}/>
                    <Route path="/dashboard/transactions" element={<TransactionsPage/>}/>
                    <Route path="/dashboard/settings" element={<SettingsPage/>}/>
                </Routes> */}
                <Outlet/>
            </div>


        </div>
    )
}

export default DashboardPage;