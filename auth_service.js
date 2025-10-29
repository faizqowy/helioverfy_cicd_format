// Save as: test_files/auth_service.js
const express = require('express');
const app = express();
const port = 3001; // As defined in docker-compose

// This route corresponds to operationId: loginUser
// It doesn't need auth middleware, because it's the route *giving* auth
app.post('/auth/login', (req, res) => {
  res.json({ token: 'fake-jwt-token' });
});

app.listen(port, () => {
  console.log(`Auth-Service listening on port ${port}`);
});