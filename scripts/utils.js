/**
 * Handles either raising a notification error or just console logging an error.
 *
 * @param {string} errMsg The message to output.
 */
export const logger = (errMsg) => {
  console.error(errMsg);
  if (game.settings.get("pf1e-compendium-zhtw", "enableDebug")) {
    ui.notifications.error(errMsg);
  }
};
