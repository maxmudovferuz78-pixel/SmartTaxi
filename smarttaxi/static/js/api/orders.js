/**
 * SmartTaxi — Orders API
 * /api/orders/ endpointlari
 */

const OrdersAPI = {
  /** Buyurtmalar ro'yxati */
  list(params = {}) {
    return api.get('/api/orders/', params);
  },

  /** Bitta buyurtma */
  get(id) {
    return api.get(`/api/orders/${id}/`);
  },

  /** Yangi buyurtma yaratish */
  create(payload) {
    return api.post('/api/orders/', payload);
  },

  /** Buyurtmani yangilash */
  update(id, payload) {
    return api.patch(`/api/orders/${id}/`, payload);
  },

  /** Buyurtmani o'chirish */
  delete(id) {
    return api.delete(`/api/orders/${id}/`);
  },

  /** Haydovchi biriktirish (operator) */
  assignDriver(orderId, driverId) {
    return api.patch(`/api/orders/${orderId}/assign_driver/`, { driver_id: driverId });
  },

  /**
   * Buyurtma statusini o'zgartirish
   * status: accepted | arrived | started | done | cancelled
   */
  setStatus(orderId, status) {
    return api.patch(`/api/orders/${orderId}/set_status/`, { status });
  },

  /** Tariflar ro'yxati */
  getTariffs() {
    return api.get('/api/tariffs/');
  },
};
window.OrdersAPI = OrdersAPI;
