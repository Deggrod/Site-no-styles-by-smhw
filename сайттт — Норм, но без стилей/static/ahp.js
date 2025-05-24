class AHPCalculator {
  constructor() {
    this.criteria = ['Соответствие интересам', 'Полезность для карьеры', 'Уровень сложности'];
    this.matrix = this.initializeMatrix();
    this.weights = [];
    this.consistencyRatio = 0;
    this.chart = null;

    this.initEventListeners();
    this.renderCriteriaList();
    this.renderMatrix();
  }

  initializeMatrix() {
    const size = this.criteria.length;
    return Array(size).fill().map((_, i) => 
      Array(size).fill().map((_, j) => (i === j) ? 1 : (i < j) ? 1 : null)
    );
  }

  initEventListeners() {
    // Добавление нового критерия
    document.getElementById('add-criterion').addEventListener('click', () => {
      const input = document.getElementById('new-criterion');
      const criterion = input.value.trim();
      
      if (criterion && !this.criteria.includes(criterion)) {
        this.criteria.push(criterion);
        this.matrix = this.initializeMatrix();
        this.renderCriteriaList();
        this.renderMatrix();
        input.value = '';
        this.hideResults();
      }
    });

    // Сброс критериев
    document.getElementById('reset-criteria').addEventListener('click', () => {
      if (confirm('Вы уверены, что хотите сбросить все критерии?')) {
        this.criteria = ['Соответствие интересам', 'Полезность для карьеры', 'Уровень сложности'];
        this.matrix = this.initializeMatrix();
        this.renderCriteriaList();
        this.renderMatrix();
        this.hideResults();
      }
    });

    // Расчет весов
    document.getElementById('calculate-btn').addEventListener('click', () => {
      if (this.validateMatrix()) {
        this.calculateWeights();
      } else {
        alert('Заполните все значения в матрице сравнений!');
      }
    });

    // Подбор треков
    document.getElementById('suggest-tracks-btn').addEventListener('click', () => {
      this.suggestTracks();
    });
  }

  renderCriteriaList() {
    const container = document.getElementById('criteria-list');
    container.innerHTML = this.criteria.map(criterion => 
      `<div class="criterion-tag">${criterion}</div>`
    ).join('');
  }

  renderMatrix() {
    const table = document.getElementById('ahp-matrix');
    table.innerHTML = '';

    // Заголовки столбцов
    const headerRow = document.createElement('tr');
    headerRow.appendChild(document.createElement('th'));
    this.criteria.forEach(criterion => {
      const th = document.createElement('th');
      th.textContent = criterion;
      headerRow.appendChild(th);
    });
    table.appendChild(headerRow);

    // Строки матрицы
    this.criteria.forEach((rowName, i) => {
      const row = document.createElement('tr');
      const th = document.createElement('th');
      th.textContent = rowName;
      row.appendChild(th);

      this.criteria.forEach((_, j) => {
        const td = document.createElement('td');
        
        if (i === j) {
          td.textContent = '1';
          td.className = 'diagonal-cell';
        } else if (i < j) {
          const input = document.createElement('input');
          input.type = 'number';
          input.min = '1';
          input.max = '9';
          input.value = this.matrix[i][j];
          input.dataset.row = i;
          input.dataset.col = j;
          input.addEventListener('change', (e) => this.updateMatrix(e));
          td.appendChild(input);
        } else {
          td.textContent = this.matrix[i][j] ? (1/this.matrix[j][i]).toFixed(3) : '';
          td.className = 'reciprocal-cell';
        }

        row.appendChild(td);
      });
      table.appendChild(row);
    });
  }

  updateMatrix(event) {
    const row = parseInt(event.target.dataset.row);
    const col = parseInt(event.target.dataset.col);
    const value = parseFloat(event.target.value);

    if (value >= 1 && value <= 9) {
      this.matrix[row][col] = value;
      this.matrix[col][row] = 1/value;
      this.renderMatrix();
      this.hideResults();
    } else {
      alert('Введите значение от 1 до 9');
      event.target.value = this.matrix[row][col];
    }
  }

  validateMatrix() {
    for (let i = 0; i < this.criteria.length; i++) {
      for (let j = i+1; j < this.criteria.length; j++) {
        if (!this.matrix[i][j] || this.matrix[i][j] < 1 || this.matrix[i][j] > 9) {
          return false;
        }
      }
    }
    return true;
  }

  calculateWeights() {
    fetch('/api/ahp/calculate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCSRFToken()
      },
      body: JSON.stringify({
        matrix: this.matrix,
        criteria: this.criteria
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        this.weights = data.weights;
        this.consistencyRatio = data.consistency_ratio;
        this.displayResults(data.is_consistent);
        document.getElementById('suggest-tracks-btn').disabled = false;
      } else {
        throw new Error(data.message);
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('Ошибка при расчете: ' + error.message);
    });
  }

  suggestTracks() {
    fetch('/api/tracks/suggest', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCSRFToken()
      },
      body: JSON.stringify({
        weights: this.weights,
        criteria: this.criteria
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        this.displayTracksSuggestions(data.suggestions);
      } else {
        throw new Error(data.message);
      }
    })
    .catch(error => {
      console.error('Error:', error);
      alert('Ошибка при подборе треков: ' + error.message);
    });
  }

  displayResults(isConsistent) {
    const resultsSection = document.getElementById('results-section');
    resultsSection.classList.remove('hidden');

    // Отображаем веса критериев
    this.renderWeightsChart();
    
    // Отображаем информацию о согласованности
    const consistencyDiv = document.getElementById('consistency-result');
    consistencyDiv.innerHTML = `
      <p>Коэффициент согласованности (CR): <strong>${this.consistencyRatio.toFixed(3)}</strong></p>
      <div class="alert ${isConsistent ? 'alert-success' : 'alert-danger'}">
        ${isConsistent ? 
          'Матрица согласована (CR ≤ 0.1)' : 
          'Внимание: матрица несогласована (CR > 0.1). Рекомендуется пересмотреть оценки!'}
      </div>
    `;
  }

  renderWeightsChart() {
    const ctx = document.getElementById('weightsChart').getContext('2d');
    
    if (this.chart) {
      this.chart.destroy();
    }
    
    this.chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: this.criteria,
        datasets: [{
          label: 'Вес критерия (%)',
          data: this.weights.map(w => w * 100),
          backgroundColor: 'rgba(54, 162, 235, 0.7)',
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            title: {
              display: true,
              text: 'Значимость (%)'
            }
          }
        }
      }
    });
  }

  displayTracksSuggestions(tracks) {
    const container = document.getElementById('tracks-list');
    container.innerHTML = tracks.map(track => `
      <div class="track-card">
        <h4>${track.name}</h4>
        <p>${track.description}</p>
        <div class="progress-container">
          <div class="progress-bar" style="width: ${track.match_percentage}%"></div>
          <span>${track.match_percentage}% соответствия</span>
        </div>
      </div>
    `).join('');

    document.querySelector('.tracks-suggestions').classList.remove('hidden');
  }

  hideResults() {
    document.getElementById('results-section').classList.add('hidden');
    document.getElementById('suggest-tracks-btn').disabled = true;
    document.querySelector('.tracks-suggestions').classList.add('hidden');
  }

  getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]').content;
  }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
  new AHPCalculator();
});