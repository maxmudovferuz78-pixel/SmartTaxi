/* Auth API */
const AuthAPI = {
  sendOtp(phone)       { return api.post('/api/auth/send-otp/', { phone }); },
  async verifyOtp(phone, code) {
    const d = await api.post('/api/auth/verify-otp/', { phone, code });
    Token.set(d.access, d.refresh);
    return d;
  },
  async me() {
    const d = await api.get('/api/auth/me/');
    localStorage.setItem('st_role', d.role||'client');
    localStorage.setItem('st_user', JSON.stringify(d));
    return d;
  },
  updateProfile(p) { return api.put('/api/auth/me/', p); },
};
window.AuthAPI = AuthAPI;
