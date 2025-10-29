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

// Case 2: "POLICY VIOLATION" (This should FAIL the CI build)
// Spec: POST /users (operationId: createUser)
// Impl: Is missing auth! Your solver should detect this policy violation.
app.post('/users', (req, res) => {
  res.status(201).send('User created');
});

// Case 3: "HEURISTIC WARNING"
// Spec: (Not defined)
// Impl: DELETE /users/:id (missing auth)
// Your SecurityAnalyzer should flag this as a warning.
app.delete('/users/:id', (req, res) => {
  res.send('User deleted');
});

// Case 4: "MISSING IMPLEMENTATION"
// Spec: GET /users/{id} (operationId: getUserById) is defined in openapi.yml
// Impl: This route is not implemented here. Your solver should create a suggestion.

app.listen(port, () => {
  console.log(`User-Service listening on port ${port}`);
});