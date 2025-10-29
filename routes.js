// Save as: user_service.js
const express = require('express');
const app = express();
const port = 3000;

// --- Middleware Definitions ---
// Your routes_parser.py will see 'auth' and 'verify' keywords
const authMiddleware = (req, res, next) => {
  console.log('Auth check for JWT');
  next();
};

const verifyAdmin = (req, res, next) => {
  console.log('Admin verification');
  next();
};

// --- Routes ---

// Case 1: "Success"
// Spec: GET /users (operationId: getUsers)
// Impl: Has 'authMiddleware'. This is fine.
app.get('/users', authMiddleware, (req, res) => {
  res.json([{ id: 1, name: 'Test User' }]);
});

// Case 2: "FIXED" (Was the Policy Violation)
// Spec: POST /users (operationId: createUser)
// Impl: NOW includes the 'authMiddleware', satisfying the policy.
app.post('/users', authMiddleware, (req, res) => {
  res.status(201).send('User created');
});

// Case 3: "FIXED" (Was the Missing Implementation)
// Spec: GET /users/{id} (operationId: getUserById) is defined in openapi.yml
// Impl: This route is now implemented.
app.get('/users/:id', authMiddleware, (req, res) => {
  res.json({ id: req.params.id, name: 'Specific User' });
});

// Case 4: "REMOVED" (Was the Security Warning)
// The DELETE /users/:id route was not in the spec, so it has been
// removed to make the implementation match the spec perfectly.
// app.delete('/users/:id', (req, res) => { ... });

app.listen(port, () => {
  console.log(`User-Service listening on port ${port}`);
});