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
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    seedDepartments();
  }, []);

  const seedDepartments = async () => {
    try {
      await axios.post(`${API}/seed/departments`);
    } catch (error) {
      // Ignore errors - departments may already be seeded
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

  const statCards = [
    {
      label: "Today's Revenue",
      value: `$${(stats?.today_revenue || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
      icon: DollarSign,
      color: "text-green-600",
      bgColor: "bg-green-100",
    },
    {
      label: "Today's Transactions",
      value: stats?.today_transactions || 0,
      icon: ShoppingCart,
      color: "text-blue-600",
      bgColor: "bg-blue-100",
    },
    {
      label: "Total Products",
      value: stats?.total_products || 0,
      icon: Package,
      color: "text-purple-600",
      bgColor: "bg-purple-100",
    },
    {
      label: "Low Stock Items",
      value: stats?.low_stock_count || 0,
      icon: AlertTriangle,
      color: "text-orange-600",
      bgColor: "bg-orange-100",
    },
    {
      label: "Total Vendors",
      value: stats?.total_vendors || 0,
      icon: Users,
      color: "text-slate-600",
      bgColor: "bg-slate-100",
    },
  ];

  return (
    <div className="p-8" data-testid="dashboard-page">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-heading font-bold text-3xl text-slate-900 uppercase tracking-wider">
          Dashboard
        </h1>
        <p className="text-slate-600 mt-1">Welcome back, {user?.name}</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8" data-testid="stats-grid">
        {statCards.map((stat, index) => (
          <div
            key={index}
            className="card-workshop p-6 animate-slide-in"
            style={{ animationDelay: `${index * 50}ms` }}
            data-testid={`stat-card-${stat.label.toLowerCase().replace(/\s+/g, "-")}`}
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
          </div>
        ))}
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Sales */}
        <div className="card-workshop p-6" data-testid="recent-sales-card">
          <div className="flex items-center justify-between mb-4 pb-4 border-b-2 border-slate-200">
            <h2 className="font-heading font-bold text-xl text-slate-900 uppercase tracking-wider">
              Recent Sales
            </h2>
            <TrendingUp className="w-5 h-5 text-slate-400" />
          </div>
          
          {stats?.recent_sales?.length > 0 ? (
            <div className="space-y-4">
              {stats.recent_sales.map((sale, index) => (
                <div
                  key={sale.id}
                  className="flex items-center justify-between p-3 bg-slate-50 rounded-sm border border-slate-200"
                  data-testid={`recent-sale-${index}`}
                >
                  <div>
                    <p className="font-mono text-sm text-slate-500">
                      {sale.id.slice(0, 8).toUpperCase()}
                    </p>
                    <p className="text-sm text-slate-600">
                      {sale.items?.length || 0} items • {sale.payment_method}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-heading font-bold text-lg text-slate-900">
                      ${sale.total?.toFixed(2)}
                    </p>
                    <p className="text-xs text-slate-400">
                      {new Date(sale.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-400">
              <ShoppingCart className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No sales recorded yet</p>
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
                  key={product.id}
                  className="flex items-center justify-between p-3 bg-orange-50 rounded-sm border border-orange-200"
                  data-testid={`low-stock-item-${index}`}
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
