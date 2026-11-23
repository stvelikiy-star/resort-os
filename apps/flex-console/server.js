// Vercel Node.js server entry point for the isolated MARINA FLEX QA project.
// No operational PMS connection and no payment endpoints. The upstream
// platform issuer and private FLEX APIs must be configured independently.
import { createServer } from 'node:http';
import { handler } from './server.mjs';

const server = createServer(handler);
if (process.env.NODE_ENV !== 'test') {
  server.listen(Number(process.env.PORT || 3000), process.env.HOST || '0.0.0.0');
}
export default server;
