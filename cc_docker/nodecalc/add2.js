const express = require('express')
const app = express()

app.get('/add/', (req, res) => {
    const [num1, num2] = req.query.id.split(' ')
    const total = (+num1) + (+num2)
    res.send('The answer is: ' + total)
})

app.listen(3000, () => console.log('Addition on 3000'))
