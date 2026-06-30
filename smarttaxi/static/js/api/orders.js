/* Orders API */
const OrdersAPI = {
  list(p={})           { return api.get('/api/orders/', p); },
  get(id)              { return api.get(`/api/orders/${id}/`); },
  create(p)            { return api.post('/api/orders/', p); }, // p: {from_address, from_lat, from_lng, to_address, to_lat, to_lng, car_type, payment_type, rush_fee, note}
  update(id,p)         { return api.patch(`/api/orders/${id}/`, p); },
  delete(id)           { return api.delete(`/api/orders/${id}/`); },
  assignDriver(oid,did){ return api.patch(`/api/orders/${oid}/assign_driver/`, {driver_id:did}); },
  setStatus(oid,s)     { return api.patch(`/api/orders/${oid}/set_status/`, {status:s}); },
  getTariffs()         { return api.get('/api/tariffs/'); },
  saveTariff(id,p)     { return id ? api.put(`/api/tariffs/${id}/`,p) : api.post('/api/tariffs/',p); },
};
window.OrdersAPI = OrdersAPI;

/* Wallet API */
const WalletAPI = {
  getBalance()       { return api.get('/api/wallet/me/'); },
  transactions(p={}) { return api.get('/api/wallet/transactions/', p); },
  topUp(amount,type) { return api.post('/api/payments/topup/', {amount,payment_type:type}); },
};
window.WalletAPI = WalletAPI;
