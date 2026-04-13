// VehicleRent — main.js

// Auto-dismiss flash alerts after 4 seconds
document.addEventListener('DOMContentLoaded', function () {
  setTimeout(function () {
    document.querySelectorAll('.alert.alert-dismissible').forEach(function (alert) {
      var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert.close();
    });
  }, 4000);
});

// Set minimum datetime for booking inputs to now
document.addEventListener('DOMContentLoaded', function () {
  var startInput = document.getElementById('startDt');
  var endInput   = document.getElementById('endDt');

  if (startInput && endInput) {
    var now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    var minVal = now.toISOString().slice(0, 16);
    startInput.min = minVal;
    endInput.min   = minVal;

    startInput.addEventListener('change', function () {
      endInput.min = startInput.value;
    });
  }
});
