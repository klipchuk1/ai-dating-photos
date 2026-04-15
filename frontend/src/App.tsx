import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import UploadPage from "./pages/UploadPage";
import StylesPage from "./pages/StylesPage";
import GeneratingPage from "./pages/GeneratingPage";
import ResultPage from "./pages/ResultPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/styles/:userId" element={<StylesPage />} />
        <Route path="/generating/:userId" element={<GeneratingPage />} />
        <Route path="/result/:userId" element={<ResultPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
