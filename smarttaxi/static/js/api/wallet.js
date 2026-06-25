/**
 * SmartTaxi — Wallet API
 * /api/wallet/ va /api/payments/ endpointlari
 */

const WalletAPI = {
  /** Haydovchi hamyoni */
  getBalance() {
    return api.get('/api/wallet/me/');
  },

  /** Tranzaksiyalar tarixi */
  transactions(params = {}) {
    return api.get('/api/wallet/transactions/', params);
  },

  /** To'lov qo'shish (Payme / Click / QR) */
  topUp(amount, paymentType = 'qr') {
    return api.post('/api/payments/topup/', { amount, payment_type: paymentType });
  },
};
window.WalletAPI = WalletAPI;
