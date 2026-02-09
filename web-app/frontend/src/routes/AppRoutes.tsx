import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './ProtectedRoute';
import PublicRoute from './PublicRoute';
import { routes } from './routeConfig';

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        {routes.map((route) => {
          const Element = route.element;

          // Public routes (no auth required)
          if (route.public) {
            // Login page should redirect to dashboard if already logged in
            if (route.path === '/login') {
              return (
                <Route
                  key={route.path}
                  path={route.path}
                  element={
                    <PublicRoute>
                      <Element />
                    </PublicRoute>
                  }
                />
              );
            }
            // Other public routes (like onboarding)
            return <Route key={route.path} path={route.path} element={<Element />} />;
          }

          // Protected routes (auth required, may have permission requirements)
          return (
            <Route
              key={route.path}
              path={route.path}
              element={
                <ProtectedRoute
                  permissions={route.permissions}
                  allPermissions={route.allPermissions}
                  roles={route.roles}
                >
                  <Element />
                </ProtectedRoute>
              }
            />
          );
        })}

        {/* Catch all - redirect to dashboard */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
