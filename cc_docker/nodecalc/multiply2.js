const express = require('express')
const app = express()

app.get('/multiply/', (req, res) => {
    const [num1, num2] = req.query.id.split(' ')
    const total = (+num1) * (+num2)
    res.send('The answer is: ' + total)
})

app.listen(3002, () => console.log('Multiplication on 3002'))

