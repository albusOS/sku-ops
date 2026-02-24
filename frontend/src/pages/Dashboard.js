import { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import {
  DollarSign,
  ShoppingCart,
  Package,
  AlertTriangle,
  Users,
  TrendingUp,
  HardHat,
  Clock,
  CheckCircle,
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const isContractor = user?.role === "contractor";
  const isAdmin = user?.role === "admin";

  useEffect(() => {
    fetchStats();
    if (!isContractor) {
      seedDepartments();
    }
  }, []);

  const seedDepartments = async () => {
    try {
      await axios.post(`${API}/seed/departments`);
    } catch (error) {
      // Ignore - may already be seeded
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error("Error fetching stats:", error);
      toast.error("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="text-slate-600 font-heading text-xl uppercase tracking-wider">
          Loading Dashboard...
        </div>
      </div>
    );
  }

  // Contractor Dashboard
  if (isContractor) {
    return (
      <div className="p-8" data-testid="dashboard-page">
        <div className="mb-8">
          <h1 className="font-heading font-bold text-3xl text-slate-900 uppercase tracking-wider">
            Dashboard
          </h1>
          <p className="text-slate-600 mt-1">
            Welcome back, {user?.name} • {user?.company || "Independent"}
          </p>
        </div>

        {/* Contractor Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="card-workshop p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-blue-100 rounded-sm flex items-center justify-center">
                <ShoppingCart className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <p className="text-sm text-slate-500 uppercase tracking-wide font-semibold">
              Total Withdrawals
            </p>
            <p className="text-3xl font-heading font-bold text-slate-900 mt-1">
              {stats?.total_withdrawals || 0}
            </p>
          </div>

          <div className="card-workshop p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-green-100 rounded-sm flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <p className="text-sm text-slate-500 uppercase tracking-wide font-semibold">
              Total Value
            </p>
            <p className="text-3xl font-heading font-bold text-green-600 mt-1">
              ${(stats?.total_spent || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </p>
          </div>

          <div className="card-workshop p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-orange-100 rounded-sm flex items-center justify-center">
                <Clock className="w-6 h-6 text-orange-600" />
              </div>
            </div>
            <p className="text-sm text-slate-500 uppercase tracking-wide font-semibold">
              Unpaid Balance
            </p>
            <p className="text-3xl font-heading font-bold text-orange-600 mt-1">
              ${(stats?.unpaid_balance || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        {/* Recent Withdrawals */}
        <div className="card-workshop p-6">
          <h2 className="font-heading font-bold text-xl text-slate-900 uppercase tracking-wider mb-4">
            Recent Withdrawals
          </h2>
          {stats?.recent_withdrawals?.length > 0 ? (
            <div className="space-y-4">
              {stats.recent_withdrawals.map((w, index) => (
                <div
                  key={w.id || index}
                  className="flex items-center justify-between p-4 bg-slate-50 rounded-sm border border-slate-200"
                >
                  <div>
                    <p className="font-mono text-sm text-slate-500">
                      Job: {w.job_id}
                    </p>
                    <p className="text-sm text-slate-600">
                      {w.items?.length || 0} items • {w.service_address?.slice(0, 30)}...
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-heading font-bold text-lg text-slate-900">
                      ${w.total?.toFixed(2)}
                    </p>
                    <span className={w.payment_status === "paid" ? "badge-success" : "badge-warning"}>
                      {w.payment_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-400">
              <ShoppingCart className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No withdrawals yet</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Warehouse Manager / Admin Dashboard
  const statCards = [
    {
      label: "Today's Activity",
      value: `$${(stats?.today_revenue || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
      subtext: `${stats?.today_transactions || 0} withdrawals`,
      icon: DollarSign,
      color: "text-green-600",
      bgColor: "bg-green-100",
    },
    {
      label: "Total Products",
      value: stats?.total_products || 0,
      icon: Package,
      color: "text-blue-600",
      bgColor: "bg-blue-100",
    },
    {
      label: "Low Stock Items",
      value: stats?.low_stock_count || 0,
      icon: AlertTriangle,
      color: "text-orange-600",
      bgColor: "bg-orange-100",
    },
    {
      label: "Contractors",
      value: stats?.total_contractors || 0,
      icon: HardHat,
      color: "text-purple-600",
      bgColor: "bg-purple-100",
      adminOnly: true,
    },
    {
      label: "Total Vendors",
      value: stats?.total_vendors || 0,
      icon: Users,
      color: "text-slate-600",
      bgColor: "bg-slate-100",
    },
  ];

  // Filter admin-only cards for non-admin users
  const displayCards = statCards.filter(card => !card.adminOnly || isAdmin);

  return (
    <div className="p-8" data-testid="dashboard-page">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-heading font-bold text-3xl text-slate-900 uppercase tracking-wider">
          Dashboard
        </h1>
        <p className="text-slate-600 mt-1">Welcome back, {user?.name}</p>
      </div>

      {/* Unpaid Alert for Admin */}
      {isAdmin && stats?.unpaid_total > 0 && (
        <div className="card-workshop p-4 mb-6 bg-red-50 border-red-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-6 h-6 text-red-600" />
              <div>
                <p className="font-semibold text-red-800">Unpaid Balance</p>
                <p className="text-sm text-red-600">Outstanding contractor withdrawals</p>
              </div>
            </div>
            <p className="font-heading font-bold text-2xl text-red-600">
              ${(stats?.unpaid_total || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </p>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-${displayCards.length} gap-6 mb-8`} data-testid="stats-grid">
        {displayCards.map((stat, index) => (
          <div
            key={index}
            className="card-workshop p-6 animate-slide-in"
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <div className="flex items-center justify-between mb-3">
              <div className={`w-12 h-12 ${stat.bgColor} rounded-sm flex items-center justify-center`}>
                <stat.icon className={`w-6 h-6 ${stat.color}`} />
              </div>
            </div>
            <p className="text-sm text-slate-500 uppercase tracking-wide font-semibold">
              {stat.label}
            </p>
            <p className="text-2xl font-heading font-bold text-slate-900 mt-1">
              {stat.value}
            </p>
            {stat.subtext && (
              <p className="text-xs text-slate-400 mt-1">{stat.subtext}</p>
            )}
          </div>
        ))}
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Withdrawals */}
        <div className="card-workshop p-6" data-testid="recent-sales-card">
          <div className="flex items-center justify-between mb-4 pb-4 border-b-2 border-slate-200">
            <h2 className="font-heading font-bold text-xl text-slate-900 uppercase tracking-wider">
              Recent Withdrawals
            </h2>
            <TrendingUp className="w-5 h-5 text-slate-400" />
          </div>

          {stats?.recent_withdrawals?.length > 0 ? (
            <div className="space-y-4">
              {stats.recent_withdrawals.map((w, index) => (
                <div
                  key={w.id || index}
                  className="flex items-center justify-between p-3 bg-slate-50 rounded-sm border border-slate-200"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <HardHat className="w-4 h-4 text-slate-400" />
                      <span className="font-medium text-slate-800">
                        {w.contractor_name || "Unknown"}
                      </span>
                    </div>
                    <p className="text-sm text-slate-500">
                      {w.items?.length || 0} items • Job: {w.job_id}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-heading font-bold text-lg text-slate-900">
                      ${w.total?.toFixed(2)}
                    </p>
                    <span className={w.payment_status === "paid" ? "badge-success" : "badge-warning"}>
                      {w.payment_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-400">
              <ShoppingCart className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No withdrawals recorded yet</p>
            </div>
          )}
        </div>

        {/* Low Stock Alerts */}
        <div className="card-workshop p-6" data-testid="low-stock-card">
          <div className="flex items-center justify-between mb-4 pb-4 border-b-2 border-slate-200">
            <h2 className="font-heading font-bold text-xl text-slate-900 uppercase tracking-wider">
              Low Stock Alerts
            </h2>
            <AlertTriangle className="w-5 h-5 text-orange-500" />
          </div>

          {stats?.low_stock_alerts?.length > 0 ? (
            <div className="space-y-3">
              {stats.low_stock_alerts.map((product, index) => (
                <div
                  key={product.id || index}
                  className="flex items-center justify-between p-3 bg-orange-50 rounded-sm border border-orange-200"
                >
                  <div>
                    <p className="font-mono text-sm text-orange-700">{product.sku}</p>
                    <p className="font-medium text-slate-800">{product.name}</p>
                  </div>
                  <div className="text-right">
                    <span className="badge-warning">{product.quantity} left</span>
                    <p className="text-xs text-slate-500 mt-1">
                      Min: {product.min_stock}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-400">
              <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>All products are well stocked</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
