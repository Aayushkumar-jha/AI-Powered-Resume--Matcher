import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import JobsPage from "./pages/JobsPage";
import NewJobPage from "./pages/NewJobPage";
import JobWorkspace from "./pages/JobWorkspace";
import RequirementsPage from "./pages/RequirementsPage";
import ResumesPage from "./pages/ResumesPage";
import DashboardPage from "./pages/DashboardPage";
import CandidatePage from "./pages/CandidatePage";
import ComparePage from "./pages/ComparePage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<JobsPage />} />
        <Route path="jobs/new" element={<NewJobPage />} />
        <Route path="jobs/:jobId" element={<JobWorkspace />}>
          <Route index element={<Navigate to="requirements" replace />} />
          <Route path="requirements" element={<RequirementsPage />} />
          <Route path="resumes" element={<ResumesPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="candidates/:candidateId" element={<CandidatePage />} />
          <Route path="compare" element={<ComparePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
