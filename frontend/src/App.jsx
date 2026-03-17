import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { queryClient } from "./lib/query-client";
import { ROLES } from "./lib/constants";
import { useRealtimeSync } from "./hooks/useRealtimeSync";
import { RealtimeSyncContext } from "./context/RealtimeSyncContext";
import Login from "./pages/Login";
import Layout from "./components/Layout";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Inventory = lazy(() => import("./pages/inventory"));
const CycleCountsPage = lazy(() => import("./pages/inventory/CycleCountsPage"));
const CycleCountDetailPage = lazy(() => import("./pages/inventory/CycleCountDetailPage"));
const Reports = lazy(() => import("./pages/Reports"));
const PointOfSale = lazy(() => import("./pages/operations/PointOfSale"));
const DirectIssue = lazy(() => import("./pages/operations/POS"));
const RequestMaterials = lazy(() => import("./pages/operations/RequestMaterials"));
const ScanModePage = lazy(() => import("./pages/operations/ScanModePage"));
const Contractors = lazy(() => import("./pages/operations/Contractors"));
const Departments = lazy(() => import("./pages/operations/Departments"));
const Vendors = lazy(() => import("./pages/operations/Vendors"));
const Purchasing = lazy(() => import("./pages/operations/Purchasing"));
const MyHistory = lazy(() => import("./pages/operations/MyHistory"));
const Jobs = lazy(() => import("./pages/operations/Jobs"));
const XeroHealthPage = lazy(() => import("./pages/finance/XeroHealthPage"));
const SettingsPage = lazy(() => import("./pages/settings/SettingsPage"));
const ProductScanLanding = lazy(() => import("./pages/ProductScanLanding"));

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen bg-muted flex items-center justify-center">
        <div className="text-muted-foreground font-heading text-xl uppercase tracking-wider">
          Loading...
        </div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (allowedRoles && !allowedRoles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
};

function RealtimeSync({ children }) {
  const value = useRealtimeSync();
  return <RealtimeSyncContext.Provider value={value}>{children}</RealtimeSyncContext.Provider>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Toaster position="top-center" richColors />
          <ErrorBoundary>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <RealtimeSync>
                      <Layout>
                        <ErrorBoundary>
                          <Suspense
                            fallback={
                              <div className="min-h-[50vh] flex items-center justify-center">
                                <div className="text-muted-foreground font-heading text-sm uppercase tracking-wider">
                                  Loading...
                                </div>
                              </div>
                            }
                          >
                            <Routes>
                              <Route path="/" element={<Dashboard />} />
                              <Route
                                path="/pos"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
                                    <PointOfSale />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/pos/issue"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
                                    <DirectIssue />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/pos/scan"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.CONTRACTOR, ROLES.ADMIN]}>
                                    <ScanModePage />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/request-materials"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.CONTRACTOR]}>
                                    <RequestMaterials />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/scan"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.CONTRACTOR, ROLES.ADMIN]}>
                                    <ScanModePage />
                                  </ProtectedRoute>
                                }
                              />
                              <Route path="/operations" element={<Navigate to="/pos" replace />} />
                              <Route
                                path="/pending-requests"
                                element={<Navigate to="/pos" replace />}
                              />
                              <Route
                                path="/inventory"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
                                    <Inventory />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/cycle-counts"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
                                    <CycleCountsPage />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/cycle-counts/:countId"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
                                    <CycleCountDetailPage />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/vendors"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
                                    <Vendors />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/departments"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
                                    <Departments />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/purchasing"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
                                    <Purchasing />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/import"
                                element={<Navigate to="/purchasing" replace />}
                              />
                              <Route
                                path="/purchase-orders"
                                element={<Navigate to="/purchasing" replace />}
                              />
                              <Route
                                path="/reports"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
                                    <Reports />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/contractors"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
                                    <Contractors />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/jobs"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
                                    <Jobs />
                                  </ProtectedRoute>
                                }
                              />
                              <Route path="/financials" element={<Navigate to="/pos" replace />} />
                              <Route path="/invoices" element={<Navigate to="/pos" replace />} />
                              <Route path="/payments" element={<Navigate to="/pos" replace />} />
                              <Route
                                path="/billing-entities"
                                element={<Navigate to="/contractors" replace />}
                              />
                              <Route
                                path="/xero-health"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
                                    <XeroHealthPage />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/product/scan/:code"
                                element={
                                  <ProtectedRoute>
                                    <ProductScanLanding />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/settings"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.ADMIN]}>
                                    <SettingsPage />
                                  </ProtectedRoute>
                                }
                              />
                              <Route
                                path="/my-history"
                                element={
                                  <ProtectedRoute allowedRoles={[ROLES.CONTRACTOR]}>
                                    <MyHistory />
                                  </ProtectedRoute>
                                }
                              />
                            </Routes>
                          </Suspense>
                        </ErrorBoundary>
                      </Layout>
                    </RealtimeSync>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </ErrorBoundary>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
