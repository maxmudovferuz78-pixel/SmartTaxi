/* Drivers API */
const DriversAPI = {
  list(p={})        { return api.get('/api/drivers/', p); },
  get(id)           { return api.get(`/api/drivers/${id}/`); },
  create(p)         { return api.post('/api/drivers/', p); },
  update(id,p)      { return api.patch(`/api/drivers/${id}/`, p); },
  delete(id)        { return api.delete(`/api/drivers/${id}/`); },
  toggleActive(id,r){ return api.patch(`/api/drivers/${id}/toggle_active/`, { reason:r }); },
  me()              { return api.get('/api/drivers/me/'); },
  setStatus(on)     { return api.patch('/api/drivers/me/status/', { is_online:on }); },
  updateProfile(p)  { return api.patch('/api/drivers/me/profile/', p); },
  nearby(lat,lng,ct,r=10){ return api.get('/api/drivers/nearby/', {lat,lng,radius:r,...(ct?{car_type:ct}:{})}); },
  updateLocation(lat,lng){ return api.post('/api/locations/update/', {lat,lng}); },
};
window.DriversAPI = DriversAPI;
