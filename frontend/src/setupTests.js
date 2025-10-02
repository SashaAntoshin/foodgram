// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

if (typeof global.setImmediate === "undefined") {
	global.setImmediate = (fn, ...args) => setTimeout(fn, 0, ...args);
  }
  
if (typeof global.clearImmediate === "undefined") {
    global.clearImmediate = (id) => clearTimeout(id);
  }