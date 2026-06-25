/**
 * SmartTaxi — Drivers API
 * /api/drivers/ endpointlari
 */

const DriversAPI = {
  /** Haydovchilar ro'yxati (admin/operator) */
  list(params = {}) {
    return api.get('/api/drivers/', params);
  },

  /** Bitta haydovchi profili */
  get(id) {
    return api.get(`/api/drivers/${id}/`);
  },

  /** Yangi haydovchi yaratish */
  create(payload) {
    return api.post('/api/drivers/', payload);
  },

  /** Haydovchini yangilash */
  update(id, payload) {
    return api.patch(`/api/drivers/${id}/`, payload);
  },

  /** Haydovchini o'chirish */
  delete(id) {
    return api.delete(`/api/drivers/${id}/`);
  },

  /** Haydovchini bloklash / faollashtirish */
  toggleActive(id, reason = '') {
    return api.patch(`/api/drivers/${id}/toggle_active/`, { reason });
  },

  /** O'z profili (haydovchi uchun) */
  me() {
    return api.get('/api/drivers/me/');
  },

  /** Online / Offline o'tish */
  setStatus(isOnline) {
    return api.patch('/api/drivers/me/status/', { is_online: isOnline });
  },

  /** Mashina ma'lumotlarini yangilash */
  updateProfile(payload) {
    return api.patch('/api/drivers/me/profile/', payload);
  },

  /** Yaqin haydovchilar */
  nearby(lat, lng, carType = null, radius = 10) {
    const params = { lat, lng, radius };
    if (carType) params.car_type = carType;
    return api.get('/api/drivers/nearby/', params);
  },

  /** GPS joylashuv yuborish */
  updateLocation(lat, lng) {
    return api.post('/api/locations/update/', { lat, lng });
  },
};
window.DriversAPI = DriversAPI;
