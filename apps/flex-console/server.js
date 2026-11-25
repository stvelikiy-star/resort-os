// Vercel Node.js server entry point for the isolated MARINA FLEX QA project.
// No operational PMS connection and no payment endpoints. The upstream
// platform issuer and private FLEX APIs must be configured independently.
import { createServer } from 'node:http';
import { handler } from './server.mjs';

// Vercel owns the HTTP listener. Listening here as well crashes its runtime
// with ERR_SERVER_ALREADY_LISTEN, even when the build itself is READY.
// For standalone development run: npm start (starts server.mjs directly).
export default createServer(handler);
