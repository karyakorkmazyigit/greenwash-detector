let stream = null;

$(document).ready(function() {

  // Fotoğraf çek butonu
  $('#take-photo').click(function() {
    $('#initial-buttons').hide();
    $('#camera-view').show();
    
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(function(s) {
        stream = s;
        document.getElementById('video').srcObject = stream;
      })
      .catch(function(err) {
        console.error("Kamera erişim hatası:", err);
        alert("Kameraya erişilemedi: " + err.message);
        resetUI();
      });
  });

  // Çek butonu
  $('#capture').click(function() {
    const video = $('#video')[0];
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    
    const imageData = canvas.toDataURL('image/jpeg');
    stopCamera();

      // Önizleme alanını göster
      $('#camera-view').hide();
      $('#preview-section').show();
      $('#preview-image').attr('src', imageData);
  
      // Geçici olarak imageData’yı sakla
      $('#preview-section').data('imageData', imageData);

          //uploadPhoto(imageData);
    showResult(imageData);
  });
    
  
  });

  // Kamera iptal butonu
  $('#cancel-camera').click(function() {
    stopCamera();
    resetUI();
  });

  // Fotoğraf yükle butonu
  $('#upload-photo').click(function() {
    $('#initial-buttons').hide();
    $('#upload-section').show();
  });

  // Dosya seçme işlemi
  $('#file-input').change(function(e) {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = function(event) {
        uploadPhoto(event.target.result);
      };
      reader.readAsDataURL(file);
    }
  });

  // Yükleme iptal butonu
  $('#cancel-upload').click(function() {
    resetUI();
  });

  // Yeni fotoğraf butonu
  $('#new-photo').click(function() {
    resetUI();
  });

  function uploadPhoto(imageData) {
    $('#camera-view').hide();
    $('#preview-section').hide();
    $('#upload-section').hide();
    $('#progress-container').show();
    
    // API'ye gönderim simülasyonu
    const progressInterval = setInterval(function() {
      const progress = $('#upload-progress');
      let currentValue = parseInt(progress.attr('aria-valuenow'));
      if (currentValue < 100) {
        currentValue += 10;
        progress.css('width', currentValue + '%')
                .attr('aria-valuenow', currentValue)
                .text(currentValue + '%');
      } else {
        clearInterval(progressInterval);
        showResult(imageData);
      }
      
    }, 300);
  }

  function showResult(imageData) {

    const image = imageData;
    $('#progress-container').hide();
    $('#result-section').show();
    $('#result-image').attr('src', imageData);
    // ve diğer yanıt simülasyonları...

    $('.shape').hide();



    // API yanıtı simülasyonu (AJAX Buraya Gelecek)
    $.ajax({
      url: 'http://localhost:8000/upload',  // Backend endpoint adresi
      type: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({ image: image }),
      success: function(response) {
          console.log('Sunucu cevabı:', response);
          document.getElementById('snapshot').innerHTML += '<p>Sunucudan gelen yanıt: ' + response.message + '</p>';
      },
      error: function() {
          console.error('Yükleme başarısız');
          document.getElementById('snapshot').innerHTML += '<p style="color:red;">Yükleme başarısız.</p>';
      }
  });
    const response = {
      status: 'success',
      message: 'Fotoğraf başarıyla yüklendi',
      timestamp: new Date().toISOString(),
      size: Math.floor(Math.random() * 1000) + 500 + ' KB'
    };
    
    $('#result-data').html(`
      <p><strong>✅ Durum:</strong> ${response.status}</p>
      <p><strong>💬 Mesaj:</strong> ${response.message}</p>
      <p><strong>⏰ Zaman:</strong> ${response.timestamp}</p>
      <p><strong>📦 Boyut:</strong> ${response.size}</p>
    `);
    
  }
  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      $('#video').attr('srcObject', null);
      stream = null;
    }
  }

  function resetUI() {
    stopCamera();
    $('#initial-buttons').show();
    $('#camera-view').hide();
    $('#upload-section').hide();
    $('#progress-container').hide();
    $('#result-section').hide();
    $('#file-input').val('');
    $('#upload-progress').val(0);
    $('#progress-text').text('0%');

    $('.shape').show();

  }
;

$('#toggle-dark-mode').click(function() {
  $('body').toggleClass('dark-mode');
  const isDark = $('body').hasClass('dark-mode');
  $('#toggle-dark-mode').text(isDark ? '☀️' : '🌙');
});

// Onayla → fotoğrafı yükle
$('#confirm-photo').click(function() {
  const imageData = $('#preview-section').data('imageData');
  $('#preview-section').hide();
  uploadPhoto(imageData);
});

// Tekrar Çek → kameraya geri dön
$('#retake-photo').click(function() {
  $('#preview-section').hide();
  $('#camera-view').show();       // kamerayı geri aç
  startCamera();                  // kamerayı tekrar başlat
});

;

$('.start-btn').on('click', function(e) {
  e.preventDefault();
  $('#main').hide();        
  $('#app').slideDown();   
  $('html, body').animate({
      scrollTop: $('#app').offset().top
  }, 600);
});

function startCamera() {
  navigator.mediaDevices.getUserMedia({ video: true })
    .then(function(s) {
      stream = s;
      document.getElementById('video').srcObject = stream;
    })
    .catch(function(err) {
      console.error("Kamera erişim hatası:", err);
      alert("Kameraya erişilemedi: " + err.message);
      resetUI();
    });
}


