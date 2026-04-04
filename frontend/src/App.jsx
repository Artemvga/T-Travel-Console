import { Navigate, Route, Routes } from "react-router-dom";

import { AccountPage } from "./pages/AccountPage";
import { CityInfoPage } from "./pages/CityInfoPage";
import { FavoritesPage } from "./pages/FavoritesPage";
import { HomePage } from "./pages/HomePage";
import { RouteBuilderPage } from "./pages/RouteBuilderPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/cities" element={<CityInfoPage />} />
      <Route path="/routes" element={<RouteBuilderPage />} />
      <Route path="/favorites" element={<FavoritesPage />} />
      <Route path="/account" element={<AccountPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
