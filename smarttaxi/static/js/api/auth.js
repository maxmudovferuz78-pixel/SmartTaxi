/**
 * SmartTaxi — Auth API
 * /api/auth/ endpointlari
 */

const AuthAPI = {
  /** Telefon raqamga OTP yuborish */
  sendOtp(phone) {
    return api.post('/api/auth/send-otp/', { phone });
  },

  /** OTP tasdiqlash → tokenlar */
  async verifyOtp(phone, code) {
    const data = await api.post('/api/auth/verify-otp/', { phone, code });
    Token.set(data.access, data.refresh);
    return data;
  },

  /** Joriy foydalanuvchi profili */
  async me() {
    const data = await api.get('/api/auth/me/');
    localStorage.setItem('user_role', data.role || 'client');
    localStorage.setItem('user_data', JSON.stringify(data));
    return data;
  },

  /** Profilni yangilash */
  updateProfile(payload) {
    return api.put('/api/auth/me/', payload);
  },
};
window.AuthAPI = AuthAPI;
