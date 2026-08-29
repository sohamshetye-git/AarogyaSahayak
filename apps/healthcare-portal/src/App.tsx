import React from "react";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { LanguageProvider } from "./context/LanguageContext";
import "./i18n";

import { ashaSyncService } from "./services/AshaSyncService"; // Initialize background sync
import { AppRouter } from "./app/router";

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <LanguageProvider>
          <AppRouter />
        </LanguageProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;

