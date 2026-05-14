const mailgun = require('mailgun.js');
const FormData = require('form-data');

const mg = new mailgun(FormData).client({
  username: 'api',
  key: process.env.MAILGUN_API_KEY
});

const sendAlert = async (email, offers, filterName) => {
  try {
    const offersHTML = offers
      .map(o => `
        <div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0;">
          <h4>${o.nombre}</h4>
          <p><strong>Organismo:</strong> ${o.organismo}</p>
          <p><strong>Región:</strong> ${o.region}</p>
          <p><strong>Monto:</strong> ${o.moneda} ${o.monto_estimado}</p>
          <p><strong>Cierre:</strong> ${o.fecha_cierre}</p>
          <p><a href="${o.link}">Ver en Mercado Público</a></p>
        </div>
      `)
      .join('');

    const messageData = {
      from: `Oferta Pública Tracker <noreply@${process.env.MAILGUN_DOMAIN}>`,
      to: email,
      subject: `${offers.length} nuevas ofertas para: ${filterName}`,
      html: `
        <h2>Nuevas ofertas que coinciden con tu filtro</h2>
        <p><strong>Filtro:</strong> ${filterName}</p>
        <p><strong>Encontradas:</strong> ${offers.length}</p>
        ${offersHTML}
        <hr>
        <p><small>Si no deseas recibir más alertas, puedes desuscribirte aquí: 
          <a href="https://tu-app.vercel.app/unsubscribe?token=TOKEN">Desuscribirse</a>
        </small></p>
      `
    };

    const result = await mg.messages.create(process.env.MAILGUN_DOMAIN, messageData);
    return result;
  } catch (error) {
    console.error('Mailgun error:', error);
    throw error;
  }
};

module.exports = { sendAlert };
