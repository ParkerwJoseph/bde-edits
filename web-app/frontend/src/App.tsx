import { AuthProvider } from './context/AuthContext';
import { PermissionProvider } from './context/PermissionContext';
import { DocumentProgressProvider } from './context/DocumentProgressContext';
import { CompanyProvider } from './contexts/CompanyContext';
import { ToastProvider } from './components/common/Toast';
import AppRoutes from './routes/AppRoutes';

function App() {
  return (
    <AuthProvider>
      <PermissionProvider>
        <DocumentProgressProvider>
          <CompanyProvider>
            <ToastProvider>
              <AppRoutes />
            </ToastProvider>
          </CompanyProvider>
        </DocumentProgressProvider>
      </PermissionProvider>
    </AuthProvider>
  );
}

export default App;
