const express = require('express');
const app = express();
const port = 3000;

const authMiddleware = (req, res, next) => {
  console.log('Auth check for JWT');
  next();
};

// NEW: A validation middleware to fix the warning
const validateParams = (req, res, next) => {
  console.log('Validating request params');
  next();
};

// --- Routes ---
app.get('/users', authMiddleware, (req, res) => {
  res.json([{ id: 1, name: 'Test User' }]);
});

app.post('/users', authMiddleware, (req, res) => {
  res.status(201).send('User created');
});

// ADDED 'validateParams' to this route
app.get('/users/:id', authMiddleware, validateParams, (req, res) => {
  res.json({ id: req.params.id, name: 'Specific User' });
});

app.listen(port, () => {
  console.log(`User-Service listening on port ${port}`);
});