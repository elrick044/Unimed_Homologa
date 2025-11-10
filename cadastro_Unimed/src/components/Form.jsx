import {useForm} from 'react-hook-form';

const Form = () => {
  //Para utilizar react hook form é necessario 
   const {register, handleSubmit} = useForm(
    {
      defaultValues: {
        name: '', 
        email: '',
        password: ''
      }   
    }
   );
   const onSubmit = (data) => {
    console.log(data);
   }
  return (
    <form  className="max-w-md mx-auto p-6 bg-white rounded-lg shadow-md w-90" onSubmit={handleSubmit(onSubmit)}>
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
        <input {...register("name")} className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500" type="text" />
      </div>
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
        <input {...register("email")} className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500" type="text" />
      </div>
       <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-1">Senha</label>
        <input {...register("password")} className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500" type="password" />
      </div>

      <button type="submit" className="w-full bg-blue-600 text-white font-medium px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500">Enviar</button>
    </form>
  );
}

export default Form;